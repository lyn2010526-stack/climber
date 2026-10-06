"""Tests for the token-cheap context bypass bundle.

``MemoryContextBypass.build`` must inject only L0 abstracts by default, keep
L1 overviews behind ``include_l1``, and attach memory hits for the current
query via the memories scope.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.memory_archive.context import DEFAULT_SCOPES, MemoryContextBypass
from app.core.memory_archive.index import SemanticIndex
from app.core.memory_archive.layers import MemorySidecarService


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def _seed(user_id: str) -> None:
    service = MemorySidecarService(semantic=SemanticIndex(enabled=False))
    _run(
        service.persist(
            user_id,
            scope="reference",
            abstract="Reference library abstracts.",
            overview="## overview\nFull reference overview body.",
        )
    )
    _run(
        service.persist(
            user_id,
            scope="skills",
            abstract="Skills for the agent.",
            overview="## overview\nFull skills overview body.",
        )
    )


class StubRetriever:
    def __init__(self, hits: list[dict[str, Any]]) -> None:
        self._hits = hits

    async def search(self, user_id, scope, query, *, level=None, top_k=5):  # noqa: ARG002
        return {
            "scope": scope,
            "query": query,
            "level": level,
            "total": len(self._hits),
            "hits": self._hits,
        }


def test_build_without_sidecars_is_empty() -> None:
    bypass = MemoryContextBypass(
        sidecars=MemorySidecarService(semantic=SemanticIndex(enabled=False)),
        retriever=StubRetriever([]),
    )
    bundle = _run(bypass.build("user-context-none"))
    assert bundle["content"] == ""
    assert bundle["injected_summaries"] == 0
    assert bundle["memory_hits"] == 0


def test_build_injects_l0_by_default_and_l1_opt_in() -> None:
    user = "user-context-seeded"
    _seed(user)
    bypass = MemoryContextBypass(
        sidecars=MemorySidecarService(semantic=SemanticIndex(enabled=False)),
        retriever=StubRetriever([]),
    )

    compact = _run(bypass.build(user, scopes=("reference", "skills")))
    assert compact["injected_summaries"] == 2
    assert compact["content"].startswith("## Archived Memory Context")
    assert "Reference library abstracts." in compact["content"]
    assert "Full reference overview body" not in compact["content"]
    assert all(item["overview"] == "" for item in compact["scopes"])

    expanded = _run(bypass.build(user, scopes=("reference", "skills"), include_l1=True))
    assert "Full reference overview body" in expanded["content"]


def test_build_uses_default_scopes() -> None:
    user = "user-context-defaults"
    _seed(user)
    bypass = MemoryContextBypass(
        sidecars=MemorySidecarService(semantic=SemanticIndex(enabled=False)),
        retriever=StubRetriever([]),
    )
    bundle = _run(bypass.build(user))
    assert tuple(item["scope"] for item in bundle["scopes"]) == ("reference", "skills")


def test_build_attaches_memory_hits_for_query() -> None:
    user = "user-context-hits"
    _seed(user)
    hit = {
        "id": "m1",
        "text": "prefers weekly release notes",
        "metadata": {"memory_type": "user_preference"},
        "score": 0.95,
    }
    bypass = MemoryContextBypass(
        sidecars=MemorySidecarService(semantic=SemanticIndex(enabled=False)),
        retriever=StubRetriever([hit]),
    )
    bundle = _run(bypass.build(user, query="release notes", memory_top_k=3))
    assert bundle["memory_hits"] == 1
    assert bundle["hits"][0]["memory_type"] == "user_preference"
    assert bundle["hits"][0]["content"] == "prefers weekly release notes"


def test_default_scopes_cover_expected_directories() -> None:
    assert "memories" in DEFAULT_SCOPES
    assert set(DEFAULT_SCOPES) >= {"reference", "skills", "conversations"}

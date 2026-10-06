"""Tests for directory-scoped retrieval.

A disabled :class:`SemanticIndex` exercises the deterministic keyword
fallback over the scope's own sidecars, and a fake vector adapter proves the
``SemanticIndex`` scope-restricting ``$and`` filter plus its failure
degradation.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.core.memory_archive.index import SemanticIndex
from app.core.memory_archive.layers import MemorySidecarService
from app.core.memory_archive.retrieval import DirectoryRetriever, normalize_scope


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def _seed(user_id: str, scope: str, bodies: list[str]) -> None:
    service = MemorySidecarService(semantic=SemanticIndex(enabled=False))
    _run(
        service.persist(
            user_id,
            scope=scope,
            abstract=bodies[0] if bodies else "",
            overview=bodies[1] if len(bodies) > 1 else "",
            entry_count=1,
        )
    )


def test_keyword_fallback_finds_sidecar_hits() -> None:
    user = "user-retrieval-keyword"
    _seed(user, "reference", ["OAuth 2.0 tokens are rotated per use.", "Login flows"])
    retriever = DirectoryRetriever(semantic=SemanticIndex(enabled=False))

    result = _run(retriever.search(user, "reference", query="rotated"))
    assert result["total"] >= 1
    first = result["hits"][0]
    assert first["kind"] == "sidecar"
    assert "rotated" in first["text"].lower()
    assert first["scope"] == "reference"


def test_search_normalizes_scope() -> None:
    user = "user-retrieval-normalize"
    _seed(user, "skills", ["A useful pattern for retries."])
    retriever = DirectoryRetriever(semantic=SemanticIndex(enabled=False))

    result = _run(retriever.search(user, "//skills/", query="pattern"))
    assert result["total"] == 1
    assert result["scope"] == "skills"


def test_search_respects_level_filter() -> None:
    user = "user-retrieval-level"
    _seed(user, "conversations", ["Overview body about pacing.", "Abstract body about pacing."])
    retriever = DirectoryRetriever(semantic=SemanticIndex(enabled=False))

    result = _run(retriever.search(user, "conversations", query="pacing", level=0))
    assert result["level"] == 0
    assert all(hit["level"] == 0 for hit in result["hits"])
    assert result["total"] == 1


def test_find_sidecars_keyword_filter() -> None:
    user = "user-retrieval-find"
    _seed(user, "reference", ["Alpha body about certificates.", "Beta body about passwords."])
    retriever = DirectoryRetriever(semantic=SemanticIndex(enabled=False))

    rows = _run(retriever.find_sidecars(user, "reference", query="passwords"))
    assert len(rows) == 1
    assert "passwords" in rows[0].body.lower()


def test_empty_scope_rejected() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        normalize_scope("  /  ")


class FakeVector:
    def __init__(self) -> None:
        self.added: list[tuple[str, str, str, dict[str, Any]]] = []
        self.search_where: list[dict[str, Any] | None] = []
        self.records: dict[str, dict[str, dict[str, Any]]] = {}
        self.fail_search = False

    async def add(self, collection, doc_id, text, metadata=None):
        self.added.append((collection, str(doc_id), text, metadata or {}))
        self.records.setdefault(collection, {})[str(doc_id)] = {
            "text": text,
            "metadata": metadata or {},
        }
        return str(doc_id)

    async def search(self, collection, query, top_k=5, where=None, profile_context=None):  # noqa: ARG002
        self.search_where.append(where)
        if self.fail_search:
            raise RuntimeError("chroma down")
        results = []
        for doc_id, rec in self.records.get(collection, {}).items():
            if where is not None and rec["metadata"].get("dir") != where["$and"][1]["dir"]:
                continue
            if where is not None and rec["metadata"].get("user_id") != where["$and"][0]["user_id"]:
                continue
            results.append({"id": doc_id, "text": rec["text"], "metadata": rec["metadata"], "score": 0.9})
        return results[:top_k]


def test_semantic_index_scopes_query_by_dir_and_user(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeVector()
    monkeypatch.setattr("app.core.vector_memory.vector_memory", fake)
    idx = SemanticIndex(enabled=True)

    assert _run(idx.index("token rotation notes", scope="skills", level=2, doc_id="d1", user_id="u1")) is True
    assert _run(idx.index("token rotation notes", scope="reference", level=2, doc_id="d2", user_id="u1")) is True

    results = _run(idx.search("u1", "skills", "query", level=2, top_k=3))
    assert len(results) == 1
    assert results[0]["id"] == "d1"
    assert fake.search_where[-1] == {
        "$and": [{"user_id": "u1"}, {"dir": "skills"}, {"level": 2}],
    }


def test_semantic_index_degrades_to_empty_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeVector()
    fake.fail_search = True
    monkeypatch.setattr("app.core.vector_memory.vector_memory", fake)
    idx = SemanticIndex(enabled=True)

    assert _run(idx.search("u1", "skills", "query")) == []


def test_disabled_semantic_index_is_inert() -> None:
    idx = SemanticIndex(enabled=False)
    assert _run(idx.search("u1", "skills", "query")) == []
    assert _run(idx.index("text", scope="skills", level=2, doc_id="d", user_id="u1")) is False

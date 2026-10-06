"""Service tests for L0/L1 sidecar generation and persistence.

Credentials and vector storage are both disabled so the tests stay offline:
the default summarizer is rule-based and an inert :class:`SemanticIndex` skips
the Chroma hop. The file-backed test database provides real upserts.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.memory_archive.index import SemanticIndex
from app.core.memory_archive.layers import (
    L0_MAX_CHARS,
    MemorySidecarService,
    sidecar_service,
)
from app.core.memory_archive.summarizer import L1_MAX_CHARS
from app.storage import async_session
from app.storage.models_memory_archive import MemorySidecar


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def _offline() -> MemorySidecarService:
    return MemorySidecarService(semantic=SemanticIndex(enabled=False))


def _entries() -> list[dict[str, Any]]:
    return [
        {"path": "auth.md", "content": "OAuth 2.0 flows protect the API surface."},
        {"path": "login.md", "content": "The login endpoint accepts username and password."},
        {"path": "tokens.md", "content": "Refresh tokens are rotated on every use."},
    ]


def _count_sidecars(user_id: str, scope: str) -> int:
    async def _count() -> int:
        async with async_session() as db:
            from sqlalchemy import func, select

            return int(
                (await db.execute(
                    select(func.count(MemorySidecar.id)).where(
                        MemorySidecar.user_id == user_id,
                        MemorySidecar.scope == scope,
                    )
                )).scalar_one()
            )

    return _run(_count())


def test_summarize_directory_persists_l0_l1_pair() -> None:
    user = "user-layers-persist"
    service = _offline()
    bundle = _run(service.summarize_directory(user, "reference", _entries()))

    assert bundle.scope == "reference"
    assert bundle.generated_by == "rule"
    assert bundle.entry_count == 3
    assert bundle.abstract
    assert bundle.overview.startswith("# Directory Overview")
    assert _count_sidecars(user, "reference") == 2

    l0, l1 = _run(service.read_pair(user, "reference"))
    assert l0 is not None
    assert l1 is not None
    assert l0.level == 0
    assert l1.level == 1
    assert len(l0.body) <= L0_MAX_CHARS
    assert len(l1.body) <= L1_MAX_CHARS


def test_refresh_upserts_in_place() -> None:
    user = "user-layers-upsert"
    service = _offline()
    _run(service.summarize_directory(user, "skills", _entries()))
    _run(service.summarize_directory(user, "skills", _entries()[:1]))

    assert _count_sidecars(user, "skills") == 2
    bundle = _run(service.summarize_directory(user, "skills", _entries()[:1]))
    assert bundle.entry_count == 1


def test_scope_is_normalized_before_persistence() -> None:
    user = "user-layers-normalize"
    service = _offline()
    _run(service.summarize_directory(user, "//conversations/", _entries()))
    assert _count_sidecars(user, "conversations") == 2


def test_missing_sidecar_reads_return_none() -> None:
    service = _offline()
    l0, l1 = _run(service.read_pair("user-layers-absent", "ghost"))
    assert l0 is None
    assert l1 is None
    assert _run(service.has_sidecar("user-layers-absent", "ghost", 0)) is False


def test_list_scopes_returns_distinct_scopes() -> None:
    user = "user-layers-scopes"
    service = _offline()
    _run(service.summarize_directory(user, "reference", _entries()))
    _run(service.summarize_directory(user, "skills", _entries()))
    assert _run(service.list_scopes(user)) == ["reference", "skills"]


def test_persist_mirrors_sidecars_to_memfs() -> None:
    class FakeMemFS:
        def __init__(self) -> None:
            self.writes: list[tuple[str, str]] = []

        async def write(self, path: str, body: str) -> None:
            self.writes.append((path, body))

    user = "user-layers-memfs"
    service = _offline()
    fs = FakeMemFS()
    _run(service.summarize_directory(user, "reference", _entries(), memfs=fs))

    paths = {path for path, _ in fs.writes}
    assert paths == {"reference/.abstract.md", "reference/.overview.md"}
    assert fs.writes[0][1]  # abstract body present


def test_singleton_service_defaults_to_rule_generation(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(sidecar_service, "_semantic", SemanticIndex(enabled=False))
    user = "user-layers-singleton"
    bundle = _run(sidecar_service.summarize_directory(user, "reference", _entries()))
    assert bundle.generated_by == "rule"

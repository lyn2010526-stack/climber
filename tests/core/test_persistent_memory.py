"""Regression tests for the persistent memory subsystem.

Covers:
- episodic memories written to the vector store so retrieve_memories hits
  the vector branch instead of always falling back to keyword search
- archival passages vector doc_ids aligned to their real DB ids, plus the
  LIKE fallback still merging when the vector store is empty
- init_db creating the lifecycle_memories / personas / session_personas
  tables (previously never registered on the shared metadata)
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.persistent_memory import persistent_memory
from app.storage.models_memory import ArchivalPassage, EpisodicMemory


class FakeVector:
    """Stand-in for app.core.vector_memory.VectorMemoryService.

    Records add/search/update_access calls and mimics the where filter on
    metadata.user_id. Set `empty` to make search return no hits.
    """

    def __init__(self) -> None:
        self.added: list[tuple[str, str, str, dict[str, Any]]] = []
        self.search_calls: list[dict[str, Any]] = []
        self.access_updates: list[tuple[str, str]] = []
        self.empty = False
        self.records: dict[str, dict[str, dict[str, Any]]] = {}

    async def add(
        self,
        collection: str,
        doc_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        self.added.append((collection, str(doc_id), text, metadata or {}))
        self.records.setdefault(collection, {})[str(doc_id)] = {
            "text": text,
            "metadata": metadata or {},
        }
        return str(doc_id)

    async def search(
        self,
        collection: str,
        query: str,
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        self.search_calls.append(
            {"collection": collection, "query": query, "top_k": top_k, "where": where}
        )
        if self.empty:
            return []
        results: list[dict[str, Any]] = []
        for doc_id, rec in self.records.get(collection, {}).items():
            if where and rec["metadata"].get("user_id") != where.get("user_id"):
                continue
            results.append(
                {"id": doc_id, "text": rec["text"], "metadata": rec["metadata"], "score": 0.9}
            )
        return results[:top_k]

    async def update_access(self, collection: str, doc_id: str) -> None:
        self.access_updates.append((collection, str(doc_id)))


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def test_create_episodic_memory_writes_vector_and_retrieve_hits(
    monkeypatch: Any,
) -> None:
    fake = FakeVector()
    monkeypatch.setattr("app.core.persistent_memory.vector_memory", fake)
    user = "user-episodic-vector"

    memory: EpisodicMemory = _run(
        persistent_memory.create_episodic_memory(
            user_id=user,
            content="quantum banana warehouse inventory",
            importance=0.2,
        )
    )

    assert any(
        col == "episodic" and doc_id == memory.id for col, doc_id, _, _ in fake.added
    )

    high = _run(
        persistent_memory.create_episodic_memory(
            user_id=user,
            content="unrelated high importance note",
            importance=0.95,
        )
    )
    results = _run(
        persistent_memory.retrieve_memories(user, query="quantum", limit=10)
    )
    assert any(c["collection"] == "episodic" for c in fake.search_calls)
    returned_ids = [m.id for m in results]
    assert memory.id in returned_ids
    assert high.id in returned_ids
    # Vector ordering wins over keyword ranking by importance.
    assert results[0].id == memory.id


def test_retrieve_keyword_fallback_when_vector_empty(monkeypatch: Any) -> None:
    fake = FakeVector()
    fake.empty = True
    monkeypatch.setattr("app.core.persistent_memory.vector_memory", fake)
    user = "user-episodic-fallback"

    memory: EpisodicMemory = _run(
        persistent_memory.create_episodic_memory(
            user_id=user,
            content="the gateway routes traffic on port 9000",
            importance=0.8,
        )
    )

    results = _run(
        persistent_memory.retrieve_memories(user, query="gateway routing", limit=5)
    )
    assert any(c["collection"] == "episodic" for c in fake.search_calls)
    assert [m.id for m in results][:1] == [memory.id]


def test_create_archival_passage_vector_id_aligned(monkeypatch: Any) -> None:
    fake = FakeVector()
    monkeypatch.setattr("app.core.persistent_memory.vector_memory", fake)
    user = "user-archival-vector"

    passage: ArchivalPassage = _run(
        persistent_memory.create_archival_passage(
            user_id=user,
            text="deployment playbook for the staging cluster",
            archive_id="arch-2026-09-19",
        )
    )

    assert any(
        col == "archival" and doc_id == passage.id
        for col, doc_id, _, _ in fake.added
    )

    results = _run(persistent_memory.search_archival_memories(user, query="deployment"))
    assert any(c["collection"] == "archival" for c in fake.search_calls)
    assert [p.id for p in results] == [passage.id]
    assert any(col == "archival" and doc_id == passage.id for col, doc_id in fake.access_updates)


def test_archival_like_fallback_when_vector_empty(monkeypatch: Any) -> None:
    fake = FakeVector()
    fake.empty = True
    monkeypatch.setattr("app.core.persistent_memory.vector_memory", fake)
    user = "user-archival-like"

    passage: ArchivalPassage = _run(
        persistent_memory.create_archival_passage(
            user_id=user,
            text="rollback procedure for the payments microservice",
            archive_id="arch-rollback",
        )
    )

    results = _run(
        persistent_memory.search_archival_memories(user, query="payments")
    )
    assert any(c["collection"] == "archival" for c in fake.search_calls)
    assert [p.id for p in results] == [passage.id]


def test_init_db_creates_memory_tables() -> None:

    from sqlalchemy import inspect
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.storage import Base

    async def _check() -> list[str]:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                tables: list[str] = await conn.run_sync(
                    lambda sync_conn: inspect(sync_conn).get_table_names()
                )
                return tables
        finally:
            await engine.dispose()

    tables = _run(_check())
    assert {"lifecycle_memories", "personas", "session_personas"} <= set(tables)

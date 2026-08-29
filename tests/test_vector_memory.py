"""Tests for vector memory service and integrated tools."""

from __future__ import annotations

import os
import time

import pytest

os.environ["APP_TESTING"] = "true"

from datetime import UTC

from app.core.memory_reflection import memory_reflection
from app.core.persistent_memory import persistent_memory
from app.core.vector_memory import _DefaultEmbeddingWrapper, vector_memory
from app.tools.memory_vector_tools import (
    recall_memories,
    reflect_on_task,
    register_memories,
)


@pytest.fixture(autouse=True)
def cleanup_vector_memory():
    """Clean up vector memory collections between tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        async def _cleanup():
            for collection_name in ["episodic", "archival", "reflection"]:
                try:
                    results = await vector_memory.search(collection_name, "cleanup", top_k=100)
                    for r in results:
                        await vector_memory.delete(collection_name, r["id"])
                except Exception:  # noqa: S110 - test-specific pattern
                    pass
        loop.run_until_complete(_cleanup())
    finally:
        loop.close()
    yield


class TestVectorMemoryService:
    def test_default_embedding_wrapper_config_round_trip(self):
        wrapper = _DefaultEmbeddingWrapper()

        assert wrapper.get_config() == {}
        assert isinstance(wrapper.build_from_config(wrapper.get_config()), _DefaultEmbeddingWrapper)

    @pytest.mark.asyncio
    async def test_add_and_search(self):
        doc_id = f"test-doc-1-{int(time.time())}"
        await vector_memory.add(
            collection="episodic",
            doc_id=doc_id,
            text="Python programming and machine learning",
            metadata={"user_id": "test-user"},
        )
        results = await vector_memory.search(
            collection="episodic",
            query="machine learning",
            top_k=5,
            where={"user_id": "test-user"},
        )
        assert len(results) >= 1
        assert results[0]["id"] == doc_id
        assert "Python" in results[0]["text"]

    @pytest.mark.asyncio
    async def test_search_without_where(self):
        results = await vector_memory.search(
            collection="episodic",
            query="programming",
            top_k=5,
        )
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_delete(self):
        doc_id = f"test-delete-doc-{int(time.time())}"
        await vector_memory.add(
            collection="episodic",
            doc_id=doc_id,
            text="Delete me",
            metadata={"user_id": "test-user"},
        )
        result = await vector_memory.delete(collection="episodic", doc_id=doc_id)
        assert result is True
        fetched = await vector_memory.get(collection="episodic", doc_id=doc_id)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_update_access(self):
        doc_id = f"test-access-doc-{int(time.time())}"
        await vector_memory.add(
            collection="episodic",
            doc_id=doc_id,
            text="Access test",
            metadata={"user_id": "test-user", "access_count": 0},
        )
        await vector_memory.update_access(collection="episodic", doc_id=doc_id)
        fetched = await vector_memory.get(collection="episodic", doc_id=doc_id)
        assert fetched is not None
        assert fetched["metadata"]["access_count"] >= 1

    @pytest.mark.asyncio
    async def test_count(self):
        count = await vector_memory.count(collection="episodic")
        assert isinstance(count, int)
        assert count >= 0


class TestPersistentMemoryVectorIntegration:
    @pytest.mark.asyncio
    async def test_retrieve_memories_vector_search(self):
        mem = await persistent_memory.create_episodic_memory(
            user_id="default-user",
            content="Vector search test content about AI agents",
            memory_type="observation",
            importance=0.7,
        )
        await vector_memory.add(
            collection="episodic",
            doc_id=mem.id,
            text=mem.content,
            metadata={"user_id": "default-user", "memory_id": mem.id},
        )
        results = await persistent_memory.retrieve_memories(
            user_id="default-user",
            query="AI agents",
            limit=5,
        )
        assert len(results) >= 1
        assert any(r.id == mem.id for r in results)

    @pytest.mark.asyncio
    async def test_search_archival_memories_vector(self):
        passage = await persistent_memory.create_archival_passage(
            user_id="default-user",
            text="Archival vector search test about knowledge graphs",
            archive_id="test-archive",
            tags=["test"],
        )
        await vector_memory.add(
            collection="archival",
            doc_id=passage.id,
            text=passage.text,
            metadata={"user_id": "default-user", "archive_id": "test-archive"},
        )
        results = await persistent_memory.search_archival_memories(
            user_id="default-user",
            query="knowledge graphs",
            limit=5,
        )
        assert len(results) >= 1
        assert any(r.id == passage.id for r in results)

    @pytest.mark.asyncio
    async def test_auto_archive_old_memories(self):
        mem = await persistent_memory.create_episodic_memory(
            user_id="default-user",
            content="Old memory to be archived",
            memory_type="observation",
            importance=0.1,
        )
        from datetime import datetime, timedelta

        from sqlalchemy import update as sa_update

        from app.storage import async_session
        from app.storage.models_memory import EpisodicMemory
        old_date = datetime.now(UTC) - timedelta(days=60)
        async with async_session() as db:
            await db.execute(
                sa_update(EpisodicMemory)
                .where(EpisodicMemory.id == mem.id)
                .values(created_at=old_date)
            )
            await db.commit()

        stats = await persistent_memory.auto_archive_old_memories(
            user_id="default-user",
            max_episodic_age_days=30,
            min_importance=0.3,
        )
        assert stats["archived"] >= 1


class TestMemoryReflectionVector:
    @pytest.mark.asyncio
    async def test_reflect_on_task(self):
        result = await memory_reflection.reflect_on_task(
            user_id="default-user",
            task_description="Build a REST API",
            outcome="Successfully built and deployed API",
            success=True,
            blockers=[],
            improvements=["Add rate limiting next time"],
        )
        assert "memory_id" in result
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_get_similar_reflections(self):
        await memory_reflection.reflect_on_task(
            user_id="default-user",
            task_description="Write unit tests",
            outcome="All tests passed",
            success=True,
        )
        results = await memory_reflection.get_similar_reflections(
            user_id="default-user",
            task_description="Write tests",
            limit=5,
        )
        assert isinstance(results, list)


class TestMemoryVectorTools:
    @pytest.mark.asyncio
    async def test_register_memories(self):
        result = await register_memories(
            content="Tool registration test memory",
            importance=0.6,
            memory_type="observation",
        )
        assert "registered" in result

    @pytest.mark.asyncio
    async def test_recall_memories(self):
        result = await recall_memories(query="registration test", limit=5)
        assert "Found" in result or "No memories" in result

    @pytest.mark.asyncio
    async def test_reflect_on_task_tool(self):
        result = await reflect_on_task(
            task_description="Deploy web service",
            outcome="Service running on port 8000",
            success=True,
            blockers=[],
            improvements=["Monitor logs"],
        )
        assert "recorded" in result

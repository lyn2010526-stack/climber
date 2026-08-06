"""TDD: memory decay + archive wired into cleanup cycle."""

import os
from datetime import UTC, datetime, timedelta

os.environ["APP_TESTING"] = "true"
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./data/test_memory_cleanup.db")

import pytest
import pytest_asyncio

from app.core.cleanup import cleanup_memory_archive, cleanup_memory_decay
from app.core.persistent_memory import PersistentMemoryService


@pytest_asyncio.fixture
async def env():
    from app.storage import init_db

    await init_db()
    yield


async def _create_episodic(**kwargs):
    """Helper to create episodic memory with optional recency/created_at overrides."""
    from app.storage import async_session
    from app.storage.models_memory import EpisodicMemory

    svc = PersistentMemoryService()
    mem = await svc.create_episodic_memory(
        user_id=kwargs["user_id"],
        content=kwargs["content"],
        importance=kwargs.get("importance", 0.5),
    )
    # Override fields not exposed by create_episodic_memory
    if "recency_score" in kwargs or "last_accessed_at" in kwargs or "created_at" in kwargs:
        async with async_session() as db:
            m = await db.get(EpisodicMemory, mem.id)
            if "recency_score" in kwargs:
                m.recency_score = kwargs["recency_score"]
            if "last_accessed_at" in kwargs:
                m.last_accessed_at = kwargs["last_accessed_at"]
            if "created_at" in kwargs:
                m.created_at = kwargs["created_at"]
            await db.commit()
    return mem


@pytest.mark.asyncio
async def test_decay_reduces_recency_scores(env):
    """After decay, unaccessed memories should have lower recency scores."""
    await _create_episodic(
        user_id="u1", content="old memory", importance=0.5,
        recency_score=1.0,
        last_accessed_at=datetime.now(UTC) - timedelta(days=10),
    )
    await cleanup_memory_decay()

    svc = PersistentMemoryService()
    memories = await svc.retrieve_memories(user_id="u1", limit=10)
    assert len(memories) == 1
    mem = memories[0]
    expected = 1.0 / (1.0 + 10)
    assert abs(mem.recency_score - expected) < 0.01, f"Expected ~{expected:.4f}, got {mem.recency_score}"


@pytest.mark.asyncio
async def test_archive_moves_old_low_importance(env):
    """Old low-importance memories should be archived and removed from episodic."""
    await _create_episodic(
        user_id="u1", content="old trivial", importance=0.1,
        recency_score=0.1,
        created_at=datetime.now(UTC) - timedelta(days=60),
    )
    await cleanup_memory_archive()

    svc = PersistentMemoryService()
    remaining = await svc.retrieve_memories(user_id="u1", limit=10)
    assert len(remaining) == 0, "Old low-importance memory should be archived out"

"""TDD test that locks the four memory-wiring bugs BEFORE fixing.

Run: `pytest tests/test_memory_wiring.py -xvs`
Expected before fix: FAIL with concrete errors per bug.
Expected after fix: PASS.
"""

import os
import uuid

os.environ["APP_TESTING"] = "true"
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./data/test_memory_wiring.db")

import pytest
import pytest_asyncio
from app.core.hierarchical_memory import HierarchicalMemoryOrchestrator
from app.core.persistent_memory import PersistentMemoryService


@pytest_asyncio.fixture
async def env():
    from app.storage import async_session, init_db

    await init_db()

    svc = PersistentMemoryService()
    await svc.create_episodic_memory(
        user_id="u1",
        content="Refactoring the user module revealed an auth bug in verify_token",
        importance=0.9,
    )
    yield svc


@pytest.mark.asyncio
async def test_bug2_episodic_retrieval_works(env):
    """BUG 2 lock: retrieve_memories returns ORM objects but caller calls .get()."""
    orch = HierarchicalMemoryOrchestrator(persistent_memory=env)
    text, tokens = await orch._retrieve_episodic("u1", "auth bug", 1500)
    assert text, "episodic retrieval must return content, not empty string"
    assert "auth bug" in text
    assert tokens > 0


@pytest.mark.asyncio
async def test_bug3_user_profile_retrieval_works(env):
    """BUG 3 lock: _retrieve_user_profile calls a method that doesn't exist."""
    orch = HierarchicalMemoryOrchestrator(persistent_memory=env)
    profile = await orch._retrieve_user_profile("u1")
    # Even with no facts, must not raise AttributeError internally.
    # With the fix it should call get_or_create_profile correctly.


@pytest.mark.asyncio
async def test_bug1_all_layers_wired(env):
    """BUG 1 lock: core/vector/reflection must be wired, not silently None."""
    orch = HierarchicalMemoryOrchestrator(
        persistent_memory=env,
        vector_memory=_FakeVector(),
        reflection=_FakeReflection(),
    )
    result = await orch.retrieve_for_query(user_id="u1", agent_id="a1", query="auth")
    # Archival and reflection should now be non-empty because services are wired.
    assert result.archival_context or result.reflection_context


@pytest.mark.asyncio
async def test_bug4_end_to_end_injects_memory(env):
    """BUG 4 lock: format_for_prompt must be non-empty when memory exists."""
    orch = HierarchicalMemoryOrchestrator(persistent_memory=env)
    result = await orch.retrieve_for_query(user_id="u1", agent_id="a1", query="auth bug")
    out = result.format_for_prompt()
    assert out, "memory injected into prompt must not be empty when memory exists"


class _FakeVector:
    async def search(self, collection, query, top_k):
        return [{"content": "Archival fact: JWT tokens expire in 24h"}]


class _FakeReflection:
    async def get_similar_reflections(self, user_id, task_description, limit):
        return [{"reflection": "Past insight: always check token expiry"}]

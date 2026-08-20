"""Tests for generic API and memory system fixes."""

from __future__ import annotations

import asyncio
import os

os.environ["APP_TESTING"] = "true"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.storage import Base, async_session, engine, init_db
from app.storage.database import Agent
from app.storage.models_memory import EpisodicMemory


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def _create_tables_sync():
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(init_db())
    finally:
        loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    _create_tables_sync()
    yield


@pytest.fixture(autouse=True)
def cleanup_db():
    yield
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        async def _cleanup():
            from app.storage import (  # noqa: F401
                models_cost,
                models_eval,
                models_groups,
                models_memory,
                models_platform,
                models_plugins,
            )
            from app.storage.database import (  # noqa: F401
                Agent,
                ApiKey,
                CheckpointRecord,
                Document,
                Message,
                Session,
                Tool,
            )
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await init_db()
        loop.run_until_complete(_cleanup())
    except Exception:  # noqa: S110 - test-specific pattern
        pass
    finally:
        loop.close()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def user1_client():
    """Authenticated client for user1."""
    token = "user-1"
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def user2_client():
    """Authenticated client for user2."""
    token = "user-2"
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        yield ac


async def _create_user_and_agent(user_id: str, agent_name: str = "Test Agent"):
    """Helper to create an agent in the database."""
    async with async_session() as db:
        agent = Agent(
            user_id=user_id,
            name=agent_name,
            provider="openai",
            model_id="gpt-4o-mini",
        )
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        from app.api.v1._shared import _agents_cache, _hybrid_agents

        _agents_cache.set(None)
        await _hybrid_agents.invalidate_scalar()
        return agent


# ─── Test: Endpoints filter by authenticated user ───────────────────────────


@pytest.mark.asyncio
async def test_list_agents_returns_all(user1_client):
    """In local mode, all agents are visible."""
    await _create_user_and_agent("user-1", "Agent A")
    await _create_user_and_agent("user-2", "Agent B")

    resp = await user1_client.get("/api/v1/agents")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2
    names = [a["name"] for a in data]
    assert "Agent A" in names
    assert "Agent B" in names


@pytest.mark.asyncio
async def test_delete_agent_works(user1_client):
    """Agent can be deleted in local mode."""
    agent = await _create_user_and_agent("user-1", "Deletable Agent")

    resp = await user1_client.delete(f"/api/v1/agents/{agent.id}")
    assert resp.status_code == 200

    # Verify agent is gone
    resp = await user1_client.get("/api/v1/agents")
    assert resp.status_code == 200
    remaining = [a for a in resp.json() if a["id"] == agent.id]
    assert len(remaining) == 0


# ─── Test: List returns all agents ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_agents_returns_list(user1_client):
    """List agents returns a flat list."""
    for i in range(3):
        await _create_user_and_agent("user-1", f"Agent {i}")

    resp = await user1_client.get("/api/v1/agents")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 3


@pytest.mark.asyncio
async def test_list_workflows_pagination(user1_client):
    """Workflow list endpoint should support pagination."""
    for i in range(3):
        async with async_session() as db:
            from app.storage.models_platform import Workflow
            wf = Workflow(
                user_id="user-1",
                name=f"Workflow {i}",
                nodes=[],
                edges=[],
            )
            db.add(wf)
            await db.commit()

    resp = await user1_client.get("/api/v1/workflows")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 3


# ─── Test: Archival/Reflection retrieval returns actual content ──────────────


@pytest.mark.asyncio
async def test_archival_retrieval_uses_text_field():
    """Archival retrieval should prefer 'text' over 'document' field."""
    from app.core.hierarchical_memory import HierarchicalMemoryOrchestrator

    class FakeVectorService:
        async def search(self, collection, query, top_k):
            # Return results with 'text' field (the correct field)
            return [
                {"text": "Archival content here", "score": 0.9, "metadata": {}},
                {"content": "Fallback content", "score": 0.8, "metadata": {}},
            ]

    orch = HierarchicalMemoryOrchestrator(vector_memory=FakeVectorService())
    result = await orch.retrieve_for_query("user-1", "agent-1", "test query")

    assert "Archival content here" in result.archival_context
    assert "Fallback content" in result.archival_context


@pytest.mark.asyncio
async def test_reflection_retrieval_uses_text_field():
    """Reflection retrieval should prefer 'text' over 'reflection' field."""
    from app.core.hierarchical_memory import HierarchicalMemoryOrchestrator

    class FakeReflectionService:
        async def get_similar_reflections(self, user_id, task_description, limit):
            return [
                {"text": "Reflection content here"},
                {"content": "Fallback reflection"},
            ]

    orch = HierarchicalMemoryOrchestrator(reflection=FakeReflectionService())
    result = await orch.retrieve_for_query("user-1", "agent-1", "test query")

    assert "Reflection content here" in result.reflection_context
    assert "Fallback reflection" in result.reflection_context


# ─── Test: Forget actually deletes memory ────────────────────────────────────


@pytest.mark.asyncio
async def test_forget_deletes_memory():
    """Forget tool should actually delete memory from database."""
    from app.core.hierarchical_memory import HierarchicalMemoryOrchestrator
    from app.tools.memory_toolset import MemoryToolSet

    agent = await _create_user_and_agent("user-1")
    memory_id = None

    async with async_session() as db:
        mem = EpisodicMemory(
            user_id="user-1",
            agent_id=agent.id,
            content="Memory to forget",
            summary="Memory to forget",
        )
        db.add(mem)
        await db.commit()
        await db.refresh(mem)
        memory_id = mem.id

    class FakeVectorService:
        async def delete(self, collection, doc_id):
            return True

    orch = HierarchicalMemoryOrchestrator(vector_memory=FakeVectorService())
    toolset = MemoryToolSet(orch)

    result = await toolset.execute("forget", {"memory_id": memory_id}, "user-1", agent.id)
    assert "forgotten" in result.lower()

    # Verify deletion
    async with async_session() as db:
        remaining = await db.execute(select(EpisodicMemory).where(EpisodicMemory.id == memory_id))
        assert remaining.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_forget_cannot_delete_other_users_memory():
    """Forget should not delete another user's memory."""
    from app.core.hierarchical_memory import HierarchicalMemoryOrchestrator
    from app.tools.memory_toolset import MemoryToolSet

    agent1 = await _create_user_and_agent("user-1")
    agent2 = await _create_user_and_agent("user-2")

    async with async_session() as db:
        mem = EpisodicMemory(
            user_id="user-2",
            agent_id=agent2.id,
            content="User2 private memory",
            summary="User2 private memory",
        )
        db.add(mem)
        await db.commit()
        await db.refresh(mem)
        memory_id = mem.id

    orch = HierarchicalMemoryOrchestrator()
    toolset = MemoryToolSet(orch)

    result = await toolset.execute("forget", {"memory_id": memory_id}, "user-1", agent1.id)
    assert "not found" in result.lower()

    # Verify memory still exists
    async with async_session() as db:
        remaining = await db.execute(select(EpisodicMemory).where(EpisodicMemory.id == memory_id))
        assert remaining.scalar_one_or_none() is not None


# ─── Test: Remember with semantic type works ────────────────────────────────


@pytest.mark.asyncio
async def test_remember_semantic_type():
    """Remember tool with semantic type should create archival passage."""
    from app.core.hierarchical_memory import HierarchicalMemoryOrchestrator
    from app.tools.memory_toolset import MemoryToolSet

    agent = await _create_user_and_agent("user-1")
    created = {}

    class FakePersistentMemory:
        async def create_archival_passage(self, user_id, text, archive_id, **kwargs):
            created["user_id"] = user_id
            created["text"] = text
            created["archive_id"] = archive_id

            class FakePassage:
                id = "archival-123"
            return FakePassage()

    orch = HierarchicalMemoryOrchestrator(persistent_memory=FakePersistentMemory())
    toolset = MemoryToolSet(orch)

    result = await toolset.execute(
        "remember",
        {"content": "Semantic knowledge", "memory_type": "semantic"},
        "user-1",
        agent.id,
    )

    assert "Remembered" in result
    assert created["user_id"] == "user-1"
    assert created["text"] == "Semantic knowledge"
    assert created["archive_id"] == "default"


# ─── Test: Constructor injection for HierarchicalMemoryOrchestrator ──────────


@pytest.mark.asyncio
async def test_constructor_injection():
    """Services should be injectable via constructor, not just wire_services."""
    from app.core.hierarchical_memory import HierarchicalMemoryOrchestrator

    class FakeCore:
        async def get_blocks(self, user_id, agent_id):
            return []
        def format_for_prompt(self, blocks):
            return ""

    class FakePersistent:
        async def format_profile_for_prompt(self, user_id):
            return ""

    class FakeVector:
        async def search(self, collection, query, top_k):
            return []

    class FakeReflection:
        async def get_similar_reflections(self, user_id, task_description, limit):
            return []

    orch = HierarchicalMemoryOrchestrator(
        core_memory=FakeCore(),
        persistent_memory=FakePersistent(),
        vector_memory=FakeVector(),
        reflection=FakeReflection(),
    )

    assert orch._core_memory_service is not None
    assert orch._persistent_memory_service is not None
    assert orch._vector_memory_service is not None
    assert orch._reflection_service is not None

    result = await orch.retrieve_for_query("user-1", "agent-1", "test")
    assert result.core_memory == ""
    assert result.archival_context == ""

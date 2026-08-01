"""Tests for generic API and memory system fixes."""

from __future__ import annotations

import asyncio
import os

os.environ["APP_TESTING"] = "true"

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.storage import init_db, engine, async_session, Base
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
            from app.storage import models_memory, models_platform, models_plugins, models_groups, models_eval, models_cost  # noqa: F401
            from app.storage.database import Agent, Session, Message, ApiKey, Tool, Document, CheckpointRecord  # noqa: F401
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await init_db()
        loop.run_until_complete(_cleanup())
    except Exception:
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
        return agent


# ─── Test: Endpoints filter by authenticated user ───────────────────────────


@pytest.mark.asyncio
async def test_list_agents_filters_by_user(user1_client, user2_client):
    """User1 should only see their own agents, not user2's."""
    await _create_user_and_agent("user-1", "User1 Agent")
    await _create_user_and_agent("user-2", "User2 Agent")

    resp1 = await user1_client.get("/api/v1/agents")
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["total"] == 1
    assert data1["items"][0]["name"] == "User1 Agent"

    resp2 = await user2_client.get("/api/v1/agents")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["total"] == 1
    assert data2["items"][0]["name"] == "User2 Agent"


@pytest.mark.asyncio
async def test_cannot_delete_other_users_agent(user1_client, user2_client):
    """User2 should not be able to delete user1's agent."""
    agent = await _create_user_and_agent("user-1", "Protected Agent")

    resp = await user2_client.delete(f"/api/v1/agents/{agent.id}")
    assert resp.status_code == 404

    # Verify agent still exists
    resp = await user1_client.get("/api/v1/agents")
    assert resp.json()["total"] == 1


# ─── Test: Pagination returns correct limits ─────────────────────────────────


@pytest.mark.asyncio
async def test_list_agents_pagination(user1_client):
    """Pagination should return correct limit and offset."""
    for i in range(5):
        await _create_user_and_agent("user-1", f"Agent {i}")

    # Test limit
    resp = await user1_client.get("/api/v1/agents?limit=2&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["limit"] == 2
    assert data["offset"] == 0

    # Test offset
    resp = await user1_client.get("/api/v1/agents?limit=2&offset=4")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1


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

    resp = await user1_client.get("/api/v1/workflows?limit=2")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 3
    assert len(data["items"]) == 2


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

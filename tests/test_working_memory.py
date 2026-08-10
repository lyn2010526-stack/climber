"""TDD: WorkingMemory L1 structured slots."""

import os

os.environ["APP_TESTING"] = "true"
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./data/test_working_memory.db")

import pytest
import pytest_asyncio

from app.core.working_memory import WorkingMemoryService, WorkingMemoryState


@pytest_asyncio.fixture
async def env():
    from app.storage import async_session, init_db
    from app.storage.database import Agent, Session

    await init_db()
    async with async_session() as db:
        from sqlalchemy import select
        agent = (await db.execute(select(Agent).where(Agent.id == "a1"))).scalar_one_or_none()
        if agent is None:
            db.add(Agent(id="a1", user_id="u1", name="test-agent", provider="openai", model_id="gpt-4"))
            await db.commit()
        session = (await db.execute(select(Session).where(Session.id == "s1"))).scalar_one_or_none()
        if session is None:
            db.add(Session(id="s1", user_id="u1", agent_id="a1"))
            await db.commit()
    yield


@pytest.mark.asyncio
async def test_working_memory_add_and_retrieve(env):
    svc = WorkingMemoryService()
    await svc.add_entry("s1", "goals", "Fix login bug")
    await svc.add_entry("s1", "observations", "Token expires after 1 hour")

    state = await svc.get_state("s1")
    assert state.goals == ["Fix login bug"]
    assert state.observations == ["Token expires after 1 hour"]


@pytest.mark.asyncio
async def test_working_memory_format_for_prompt(env):
    state = WorkingMemoryState(
        goals=["Fix bug"],
        observations=["Token issue"],
        progress=["Reproduced"],
    )
    prompt = state.format_for_prompt()
    assert "## Current Goals" in prompt
    assert "Fix bug" in prompt
    assert "## Observations" in prompt
    assert "Token issue" in prompt
    assert "## Progress Log" in prompt
    assert "Reproduced" in prompt


@pytest.mark.asyncio
async def test_working_memory_clear(env):
    svc = WorkingMemoryService()
    await svc.add_entry("s1", "goals", "Task")
    await svc.clear("s1")
    state = await svc.get_state("s1")
    assert state.goals == []
    assert state.observations == []

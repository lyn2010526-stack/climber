"""TDD: IdentityMemory L4 injected into system prompt."""

import os

os.environ["APP_TESTING"] = "true"
os.environ["TEST_DATABASE_URL"] = "sqlite+aiosqlite:///./data/test_identity_memory.db"

import pytest
import pytest_asyncio
from app.core.persistent_memory import PersistentMemoryService


@pytest_asyncio.fixture
async def env():
    from app.storage import async_session, init_db

    await init_db()
    yield


@pytest.mark.asyncio
async def test_identity_includes_inviolable(env):
    svc = PersistentMemoryService()
    profile = await svc.get_or_create_profile("u1")
    profile.inviolable = ["Never delete user data without confirmation"]
    profile.values = ["Privacy first"]
    profile.principles = ["Be concise"]
    from app.storage import async_session
    async with async_session() as db:
        db.add(profile)
        await db.commit()

    prompt = await svc.format_profile_for_prompt("u1")
    assert "[INVIOLABLE RULES" in prompt
    assert "Never delete user data" in prompt
    assert "Privacy first" in prompt
    assert "Be concise" in prompt


@pytest.mark.asyncio
async def test_identity_no_inviolable_when_empty(env):
    svc = PersistentMemoryService()
    prompt = await svc.format_profile_for_prompt("u1")
    assert "[INVIOLABLE RULES" not in prompt
    assert "## User Values" not in prompt
    assert "## User Principles" not in prompt

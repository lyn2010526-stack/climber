"""Coverage tests for app/core/memory/persona.py.

Uses a per-test in-memory SQLite engine (StaticPool) so the tests are
order-independent and immune to cross-test connection-pool reuse.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

import app.core.memory.persona as persona_module
from app.core.memory.persona import (
    AgentPersona,
    PersonaModel,
    PersonaStore,
    SessionPersonaModel,
    create_session_persona,
    get_effective_persona,
    merge_session_persona,
    persona_store,
)
from app.storage import Base


@pytest_asyncio.fixture
async def env(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(persona_module, "async_session", maker)
    env = SimpleNamespace(store=PersonaStore(), maker=maker)
    yield env
    await engine.dispose()


async def _insert_session_persona(
    env,
    session_id: str,
    base_persona_id: str,
    overrides: dict | None = None,
    learnings: dict | None = None,
) -> None:
    async with env.maker() as db:
        db.add(
            SessionPersonaModel(
                session_id=session_id,
                base_persona_id=base_persona_id,
                overrides=overrides or {},
                learnings=learnings or {},
            )
        )
        await db.commit()


def test_persona_format_for_prompt_full() -> None:
    persona = AgentPersona(
        agent_id="a1",
        name="Ada",
        role="Assistant",
        personality_traits=["curious", "precise"],
        expertise=["math"],
        communication_style="concise",
        goals=["be helpful", "be fast"],
    )
    text = persona.format_for_prompt()
    assert text.startswith("# Agent: Ada")
    assert "**Role:** Assistant" in text
    assert "**Traits:** curious, precise" in text
    assert "**Expertise:** math" in text
    assert "**Communication Style:** concise" in text
    assert "**Goals:**" in text
    assert "- be helpful" in text


def test_persona_format_for_prompt_minimal() -> None:
    persona = AgentPersona(agent_id="a2", name="Bare")
    text = persona.format_for_prompt()
    assert text == "# Agent: Bare"
    assert persona.to_dict()["agent_id"] == "a2"
    assert persona.created_at
    assert persona.updated_at


async def test_save_and_load_new_persona(env) -> None:
    persona = AgentPersona(agent_id="cov-persona-1", name="First", role="worker")
    saved = await env.store.save(persona)
    assert saved.updated_at

    loaded = await env.store.load("cov-persona-1")
    assert loaded is not None
    assert loaded.name == "First"
    assert loaded.role == "worker"
    assert loaded.personality_traits == []

    assert await env.store.load("cov-persona-missing") is None


async def test_save_updates_existing(env) -> None:
    await env.store.save(AgentPersona(agent_id="cov-persona-2", name="Old", role="r1"))
    await env.store.save(
        AgentPersona(
            agent_id="cov-persona-2",
            name="New",
            role="r2",
            personality_traits=["bold"],
            expertise=["ai"],
            communication_style="warm",
            goals=["g1"],
        )
    )
    loaded = await env.store.load("cov-persona-2")
    assert loaded.name == "New"
    assert loaded.role == "r2"
    assert loaded.personality_traits == ["bold"]
    assert loaded.expertise == ["ai"]
    assert loaded.communication_style == "warm"
    assert loaded.goals == ["g1"]


async def test_update_fields(env) -> None:
    await env.store.save(AgentPersona(agent_id="cov-persona-3", name="Orig"))

    assert await env.store.update("cov-persona-absent", name="x") is None

    updated = await env.store.update(
        "cov-persona-3",
        name="Renamed",
        role="lead",
        unknown_field="ignored",
        communication_style=None,  # None values are skipped
    )
    assert updated is not None
    assert updated.name == "Renamed"
    assert updated.role == "lead"
    assert updated.communication_style == ""


async def test_delete_persona(env) -> None:
    await env.store.save(AgentPersona(agent_id="cov-persona-4", name="Temp"))
    assert await env.store.delete("cov-persona-4") is True
    assert await env.store.load("cov-persona-4") is None
    assert await env.store.delete("cov-persona-4") is False


async def test_list_all(env) -> None:
    await env.store.save(AgentPersona(agent_id="cov-persona-5", name="B"))
    await env.store.save(AgentPersona(agent_id="cov-persona-6", name="A"))
    all_personas = await env.store.list_all()
    names = sorted(p.name for p in all_personas)
    assert names == ["A", "B"]


def test_create_session_persona() -> None:
    result = create_session_persona("sess-1", "base-1")
    assert result["session_id"] == "sess-1"
    assert result["base_persona_id"] == "base-1"
    assert result["overrides"] == {}
    assert result["learnings"] == {}
    assert result["created_at"]

    with_overrides = create_session_persona("sess-2", "base-2", {"name": "X"})
    assert with_overrides["overrides"] == {"name": "X"}


async def test_merge_session_persona_missing_session(env) -> None:
    assert await merge_session_persona("no-such-session") is None


async def test_merge_session_persona_missing_base(env) -> None:
    await _insert_session_persona(env, "cov-sess-nobase", "no-such-base", learnings={"x": 1})
    assert await merge_session_persona("cov-sess-nobase") is None


async def test_merge_session_persona_applies_learnings(env) -> None:
    await env.store.save(
        AgentPersona(
            agent_id="cov-persona-merge",
            name="Merge",
            expertise=["base"],
            goals=["base-goal"],
            communication_style="dry",
        )
    )
    await _insert_session_persona(
        env,
        "cov-sess-merge",
        "cov-persona-merge",
        learnings={
            "new_expertise": ["base", "extra"],
            "goal_progress": ["base-goal", "new-goal"],
            "style_feedback": "friendly",
        },
    )
    report = await merge_session_persona("cov-sess-merge")
    assert report is not None
    assert report["merged_fields"] == ["expertise", "goals", "communication_style"]

    reloaded = await env.store.load("cov-persona-merge")
    assert reloaded.expertise == ["base", "extra"]
    assert reloaded.goals == ["base-goal", "new-goal"]
    assert reloaded.communication_style == "friendly"


async def test_merge_session_persona_empty_learnings(env) -> None:
    await env.store.save(AgentPersona(agent_id="cov-persona-merge2", name="M2"))
    await _insert_session_persona(env, "cov-sess-merge2", "cov-persona-merge2")
    report = await merge_session_persona("cov-sess-merge2")
    assert report is not None
    assert report["merged_fields"] == []


async def test_get_effective_persona_variants(env) -> None:
    # base missing
    assert await get_effective_persona(None, "no-such-agent") is None

    await env.store.save(AgentPersona(agent_id="cov-persona-eff", name="Base", role="r"))

    # no session id -> base
    base = await get_effective_persona(None, "cov-persona-eff")
    assert base is not None and base.name == "Base"

    # session id but no session row -> base
    no_row = await get_effective_persona("cov-sess-missing", "cov-persona-eff")
    assert no_row is not None and no_row.name == "Base"

    # session row with empty overrides -> base
    await _insert_session_persona(env, "cov-sess-empty", "cov-persona-eff", overrides={})
    empty = await get_effective_persona("cov-sess-empty", "cov-persona-eff")
    assert empty is not None and empty.name == "Base"

    # session row with overrides -> merged persona
    await _insert_session_persona(
        env,
        "cov-sess-override",
        "cov-persona-eff",
        overrides={"name": "Overridden", "goals": ["g"]},
    )
    merged = await get_effective_persona("cov-sess-override", "cov-persona-eff")
    assert merged is not None
    assert merged.name == "Overridden"
    assert merged.role == "r"  # falls back to base
    assert merged.goals == ["g"]
    assert merged.created_at == base.created_at


async def test_persona_model_columns_and_select(env) -> None:
    async with env.maker() as db:
        rows = (await db.execute(select(PersonaModel))).scalars().all()
    assert rows == []


def test_module_singleton_is_store() -> None:
    assert isinstance(persona_store, PersonaStore)

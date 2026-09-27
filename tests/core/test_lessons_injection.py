"""Lessons injection (boundary item 2) + memory_type retrieval filter.

Covers:
- retrieve_memories(memory_type=...) filters both the vector and keyword paths.
- save_lesson builtin persists an EpisodicMemory with memory_type='lesson',
  scoped server-side from the memory context (never from model args).
- AgentEngine._inject_lessons injects a SYSTEM message only when the user
  message retrieves a lesson hit, and replaces the marker on repeat runs.

Runs with --noconftest; seeds real agents rows to satisfy the agent_id FK.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.memory_context import clear_memory_scope, set_memory_scope
from app.core.persistent_memory import persistent_memory
from app.tools.builtins import save_lesson


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def _ensure_agents(*agent_ids: str, user_id: str) -> None:
    from app.storage import async_session
    from app.storage.database import Agent

    async def _inner() -> None:
        async with async_session() as db:
            for agent_id in agent_ids:
                db.add(Agent(id=agent_id, user_id=user_id, name=agent_id, provider="openai", model_id="gpt-4o"))
            await db.commit()

    _run(_inner())


def _cleanup(user_id: str) -> None:
    from sqlalchemy import delete

    from app.storage import async_session
    from app.storage.models_memory import EpisodicMemory

    async def _inner() -> None:
        async with async_session() as db:
            await db.execute(delete(EpisodicMemory).where(EpisodicMemory.user_id == user_id))
            await db.commit()

    _run(_inner())


# ─── memory_type filter on retrieve_memories ────────────────────────────────


def test_memory_type_filter_isolates_lessons() -> None:
    _ensure_agents("agent-lsn-1", user_id="user-lsn")
    try:
        _run(persistent_memory.create_episodic_memory(
            "user-lsn", "always run pytest before commit", agent_id="agent-lsn-1",
            memory_type="lesson", importance=0.7,
        ))
        _run(persistent_memory.create_episodic_memory(
            "user-lsn", "user prefers dark mode", agent_id="agent-lsn-1",
            memory_type="preference", importance=0.7,
        ))
        lessons = _run(persistent_memory.retrieve_memories(
            "user-lsn", agent_id="agent-lsn-1", memory_type="lesson",
        ))
        assert all(m.memory_type == "lesson" for m in lessons)
        assert any("pytest" in m.content for m in lessons)
        assert all("dark mode" not in m.content for m in lessons)
        # default (no filter) still returns everything
        all_mems = _run(persistent_memory.retrieve_memories("user-lsn", agent_id="agent-lsn-1"))
        types = {m.memory_type for m in all_mems}
        assert {"lesson", "preference"} <= types
    finally:
        _cleanup("user-lsn")


def test_keyword_path_matches_lesson_by_query() -> None:
    """Vector store is absent in tests, so the keyword fallback must filter too."""
    _ensure_agents("agent-lsn-2", user_id="user-lsn2")
    try:
        _run(persistent_memory.create_episodic_memory(
            "user-lsn2", "when nginx 502s check the upstream socket first",
            agent_id="agent-lsn-2", memory_type="lesson", importance=0.7,
        ))
        hits = _run(persistent_memory.retrieve_memories(
            "user-lsn2", query="nginx 502 debugging", agent_id="agent-lsn-2", memory_type="lesson",
        ))
        assert any("nginx" in m.content for m in hits)
    finally:
        _cleanup("user-lsn2")


# ─── save_lesson tool: server-side scope ────────────────────────────────────


def test_save_lesson_persists_with_scope() -> None:
    _ensure_agents("agent-lsn-3", user_id="user-lsn3")
    set_memory_scope("user-lsn3", "agent-lsn-3")
    try:
        out = _run(save_lesson(lesson="flaky test fixed by freezing the clock", tags=["pytest", "flake"]))
        assert "Lesson saved" in out
        mems = _run(persistent_memory.retrieve_memories("user-lsn3", agent_id="agent-lsn-3", memory_type="lesson"))
        assert any("freezing the clock" in m.content for m in mems)
        assert all(m.agent_id == "agent-lsn-3" for m in mems)
        assert any("pytest" in (m.tags or []) for m in mems)
    finally:
        clear_memory_scope()
        _cleanup("user-lsn3")


def test_save_lesson_refuses_without_scope() -> None:
    clear_memory_scope()
    out = _run(save_lesson(lesson="orphan lesson"))
    assert "no active user memory scope" in out


def test_save_lesson_empty_rejected() -> None:
    set_memory_scope("user-lsn4", None)
    try:
        out = _run(save_lesson(lesson="   "))
        assert "must not be empty" in out
    finally:
        clear_memory_scope()


# ─── Engine injection: SYSTEM role, keyword-gated, marker-replaced ──────────


def _make_session(user_id: str, agent_id: str, message: str) -> Any:
    from app.core.session import AgentSession

    session = AgentSession(session_id="sess-lsn", user_id=user_id, agent_id=agent_id)
    session.messages = [{"role": "user", "content": message}]
    return session


def test_inject_lessons_adds_system_message_on_hit() -> None:
    from app.core.agent_engine import AgentEngine

    _ensure_agents("agent-lsn-5", user_id="user-lsn5")
    try:
        _run(persistent_memory.create_episodic_memory(
            "user-lsn5", "database migration must run before integration tests",
            agent_id="agent-lsn-5", memory_type="lesson", importance=0.9,
        ))
        engine = AgentEngine.__new__(AgentEngine)
        engine.memory_service = persistent_memory
        session = _make_session("user-lsn5", "agent-lsn-5", "run the integration tests after migration")
        _run(engine._inject_lessons(session, "run the integration tests after migration"))
        sys_msgs = [m for m in session.messages if m.get("role") == "system"]
        assert len(sys_msgs) == 1
        assert sys_msgs[0]["content"].startswith("<!-- LESSONS -->")
        assert "migration" in sys_msgs[0]["content"]
    finally:
        _cleanup("user-lsn5")


def test_inject_lessons_silent_when_no_match() -> None:
    from app.core.agent_engine import AgentEngine

    engine = AgentEngine.__new__(AgentEngine)
    engine.memory_service = persistent_memory
    session = _make_session("user-lsn-none", "", "completely unrelated request about cooking")
    _run(engine._inject_lessons(session, "completely unrelated request about cooking"))
    assert all(m.get("role") != "system" for m in session.messages)


def test_inject_lessons_skips_empty_message() -> None:
    from app.core.agent_engine import AgentEngine

    engine = AgentEngine.__new__(AgentEngine)
    engine.memory_service = persistent_memory
    session = _make_session("user-lsn-none", "", "")
    _run(engine._inject_lessons(session, ""))
    assert all(m.get("role") != "system" for m in session.messages)


def test_inject_lessons_replaces_marker_not_accumulates() -> None:
    from app.core.agent_engine import AgentEngine

    _ensure_agents("agent-lsn-6", user_id="user-lsn6")
    try:
        _run(persistent_memory.create_episodic_memory(
            "user-lsn6", "pytest markers select slow tests",
            agent_id="agent-lsn-6", memory_type="lesson", importance=0.9,
        ))
        engine = AgentEngine.__new__(AgentEngine)
        engine.memory_service = persistent_memory
        session = _make_session("user-lsn6", "agent-lsn-6", "pytest slow tests")
        _run(engine._inject_lessons(session, "pytest slow tests"))
        _run(engine._inject_lessons(session, "pytest slow tests"))
        sys_msgs = [m for m in session.messages if m.get("role") == "system"]
        assert len(sys_msgs) == 1  # replaced, not duplicated
    finally:
        _cleanup("user-lsn6")

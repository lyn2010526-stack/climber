"""Engine session registry lifecycle tests.

`AgentEngine.create_session` (app/core/agent_engine.py:194) inserts into
`self._sessions`, and nothing ever removes the entry. `DELETE
/api/v1/sessions/{id}` (app/api/v1/sessions.py:244) deletes the database row
only, so an in-memory session -- including `session_config.api_key` -- stays
resident for the process lifetime. Eight production call sites create
sessions (chat, crews, workflow engine, telegram bot, task worker,
collaboration runner, tools/builtins, multi_agent/crew) and none of them
releases the entry.

These tests pin the intended contract: closing a session must release both
the session and its lock, closing twice must be safe, and closing a session
that is mid-run must not disturb the running iteration.
"""

from __future__ import annotations

import asyncio

import pytest

from app.core.agent_engine import AgentEngine
from app.core.session import AgentSession


@pytest.fixture
def engine() -> AgentEngine:
    engine = AgentEngine.__new__(AgentEngine)
    engine._sessions = {}
    engine._session_locks = {}
    return engine


def _session(session_id: str = "s1") -> AgentSession:
    s = AgentSession(session_id=session_id, agent_id="a1", user_id="u1")
    s.session_config.api_key = "sk-secret-value"
    return s


def test_create_session_registers_in_memory(engine: AgentEngine) -> None:
    """Baseline: the registry does grow on every create."""
    s = engine.create_session(
        agent_id="a1",
        user_id="u1",
        provider="openai",
        model_id="gpt-4o-mini",
        api_key="sk-secret-value",
    )
    assert s.session_id in engine._sessions


def test_close_session_releases_registry_entry(engine: AgentEngine) -> None:
    """A closed session must not stay resident holding its API key."""
    s = _session()
    engine._sessions[s.session_id] = s
    engine._session_locks[s.session_id] = asyncio.Lock()

    engine.close_session(s.session_id)

    assert s.session_id not in engine._sessions
    assert s.session_id not in engine._session_locks


def test_close_session_is_idempotent(engine: AgentEngine) -> None:
    """DELETE handlers can race or retry; double close must not raise."""
    s = _session()
    engine._sessions[s.session_id] = s

    engine.close_session(s.session_id)
    engine.close_session(s.session_id)  # must not raise


def test_close_unknown_session_is_a_no_op(engine: AgentEngine) -> None:
    engine.close_session("does-not-exist")


def test_close_session_clears_api_key(engine: AgentEngine) -> None:
    """Even a retained reference must not keep the credential in memory."""
    s = _session()
    engine._sessions[s.session_id] = s

    engine.close_session(s.session_id)

    assert s.session_config.api_key == ""


def test_closed_session_is_invisible_to_permission_resolve(engine: AgentEngine) -> None:
    """A closed session must not be resolvable by a late approval POST."""
    s = _session()
    engine._sessions[s.session_id] = s
    s._pending_permission = {"tool_call_id": "tool-s1-1-1", "decision": None}
    s._permission_event = asyncio.Event()

    engine.close_session(s.session_id)

    assert engine.resolve_permission("tool-s1-1-1", "allow") is False

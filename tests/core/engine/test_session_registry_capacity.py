"""Session registry capacity tests.

`close_session` (app/core/agent_engine.py) gives sessions a release path, but
only when a caller invokes it. The eight production call sites that create
sessions -- chat, crews, workflow engine, telegram bot, task worker,
collaboration runner, tools/builtins and multi_agent/crew -- all keep the
session and then drop the reference, so the registry grows without bound and
`session_config.api_key` stays resident on every entry.

An explicit cap removes that dependence on every caller doing the right thing.
These tests pin the cap behaviour: a bounded registry evicts the least recently
touched session, the active session is never the victim, and closing a session
still works when eviction is disabled.
"""

from __future__ import annotations

import asyncio

import pytest

from app.core.agent_engine import AgentEngine
from app.core.session import AgentSession


def make_engine(max_sessions: int) -> AgentEngine:
    """Build a bare engine carrying only the registry state under test."""
    engine = AgentEngine.__new__(AgentEngine)
    engine._sessions = {}
    engine._session_locks = {}
    engine._session_order = []
    engine.max_sessions = max_sessions
    return engine


def make_session(session_id: str) -> AgentSession:
    return AgentSession(session_id=session_id, agent_id="a", user_id="u")


def test_registry_keeps_only_the_configured_number_of_sessions() -> None:
    engine = make_engine(max_sessions=2)
    for i in range(5):
        engine._register_session(make_session(f"s{i}"))

    assert set(engine._sessions) == {"s3", "s4"}


def test_eviction_releases_the_credential_it_drops() -> None:
    """An evicted session must not leave its api_key reachable."""
    engine = make_engine(max_sessions=1)
    victim = make_session("s0")
    victim.session_config.api_key = "sk-secret"
    engine._register_session(victim)
    engine._register_session(make_session("s1"))

    assert "s0" not in engine._sessions
    assert victim.session_config.api_key == ""


def test_creating_a_session_refreshes_it_so_active_work_survives() -> None:
    engine = make_engine(max_sessions=2)
    engine._register_session(make_session("old"))
    engine._register_session(make_session("mid"))
    # Touching "old" makes "mid" the least recently used entry.
    engine._register_session(engine._sessions["old"])
    engine._register_session(make_session("new"))

    assert "old" in engine._sessions
    assert "mid" not in engine._sessions
    assert "new" in engine._sessions


@pytest.mark.asyncio
async def test_running_sessions_are_never_evicted() -> None:
    """Evicting an in-flight run would strand its iteration with no registry."""
    from app.core.task_state_machine import TaskState

    engine = make_engine(max_sessions=1)
    running = make_session("running")
    engine._register_session(running)
    await running.state_machine.transition(
        TaskState.ASSIGNED, trigger="test"
    )
    await running.state_machine.transition(
        TaskState.RUNNING, trigger="test"
    )
    assert running.state_machine.state == TaskState.RUNNING
    engine._register_session(make_session("fresh"))

    assert "running" in engine._sessions
    assert "fresh" in engine._sessions


@pytest.mark.asyncio
async def test_locked_sessions_are_never_evicted_even_before_state_transition() -> None:
    """A lock is the authoritative busy signal while a run starts up."""
    engine = make_engine(max_sessions=1)
    active = make_session("active")
    engine._register_session(active)
    lock = asyncio.Lock()
    await lock.acquire()
    engine._session_locks[active.session_id] = lock

    engine._register_session(make_session("fresh"))

    assert "active" in engine._sessions
    assert "fresh" in engine._sessions


def test_cap_is_skipped_when_disabled() -> None:
    engine = make_engine(max_sessions=0)
    for i in range(4):
        engine._register_session(make_session(f"s{i}"))

    assert len(engine._sessions) == 4


def test_close_session_removes_the_lock_as_well() -> None:
    import asyncio

    engine = make_engine(max_sessions=4)
    engine._register_session(make_session("s0"))
    engine._session_locks["s0"] = asyncio.Lock()

    assert engine.close_session("s0") is True
    assert "s0" not in engine._sessions
    assert "s0" not in engine._session_locks


@pytest.mark.parametrize("bad_limit", [-1, "ten", None])
def test_invalid_limits_fall_back_to_the_default(bad_limit) -> None:
    """A bad env value must not disable the cap or crash the engine."""
    engine = AgentEngine.__new__(AgentEngine)
    engine._sessions = {}
    engine._session_locks = {}
    engine._session_order = []
    engine.max_sessions = _parse_max_sessions(bad_limit)

    assert engine.max_sessions > 0


def _parse_max_sessions(raw) -> int:
    from app.core.agent_engine import _parse_max_sessions as parse

    return parse(raw)

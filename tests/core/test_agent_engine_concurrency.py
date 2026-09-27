"""Regression tests for session lock ownership and cancellation cleanup.

Design references:

* https://docs.python.org/3/library/asyncio-task.html#task-cancellation
* https://anyio.readthedocs.io/en/stable/synchronization.html#capacity-limiters
* https://docs.langchain.com/oss/python/langgraph/use-graph-api#map-reduce-and-the-send-api
* https://docs.ray.io/en/latest/ray-core/actors/async_api.html#setting-concurrency-in-async-actors
"""

from __future__ import annotations

import asyncio

import pytest

from app.core import AgentEvent
from app.core.agent_engine import AgentEngine
from app.core.session import AgentSession
from app.core.task_state_machine import TaskState


@pytest.mark.asyncio
async def test_cancelled_run_keeps_a_replacement_lock_from_being_deleted(monkeypatch) -> None:
    engine = AgentEngine.__new__(AgentEngine)
    engine._sessions = {}
    engine._session_locks = {}
    session = AgentSession(session_id="s1", agent_id="a", user_id="u")
    started = asyncio.Event()
    release = asyncio.Event()

    async def run_locked(_session, _message):
        started.set()
        engine._session_locks[session.session_id] = asyncio.Lock()
        await release.wait()
        yield AgentEvent(type="done", data={})

    monkeypatch.setattr(engine, "_run_locked", run_locked)
    monkeypatch.setattr("app.core.agent_engine._emergency_stop_active", lambda: False)
    monkeypatch.setattr("app.core.agent_engine._observability_sinks", lambda: (None, None))

    task = asyncio.create_task(_collect(engine.run(session, "hello")))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert session.session_id in engine._session_locks


@pytest.mark.asyncio
async def test_close_session_does_not_remove_lock_while_run_is_active(monkeypatch) -> None:
    engine = AgentEngine.__new__(AgentEngine)
    engine._sessions = {}
    engine._session_locks = {}
    engine._session_order = []
    session = AgentSession(session_id="s1", agent_id="a", user_id="u")
    engine._sessions[session.session_id] = session
    started = asyncio.Event()
    release = asyncio.Event()

    async def run_locked(_session, _message):
        started.set()
        await release.wait()
        yield AgentEvent(type="done", data={})

    monkeypatch.setattr(engine, "_run_locked", run_locked)
    monkeypatch.setattr("app.core.agent_engine._emergency_stop_active", lambda: False)
    monkeypatch.setattr("app.core.agent_engine._observability_sinks", lambda: (None, None))

    task = asyncio.create_task(_collect(engine.run(session, "hello")))
    await started.wait()
    lock = engine._session_locks[session.session_id]
    assert engine.close_session(session.session_id) is True
    assert engine._session_locks.get(session.session_id) is lock

    release.set()
    await task
    assert session.session_id not in engine._session_locks


@pytest.mark.asyncio
async def test_cancelled_permission_wait_clears_pending_state() -> None:
    engine = AgentEngine.__new__(AgentEngine)
    engine.permission_timeout_seconds = 30.0
    session = AgentSession(session_id="s1", agent_id="a", user_id="u")
    session._pending_permission = {"tool_call_id": "tool-1", "decision": None}
    session._permission_event = asyncio.Event()

    task = asyncio.create_task(engine._wait_for_permission(session))
    await asyncio.sleep(0)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert session._pending_permission is None
    assert session._permission_event is None


@pytest.mark.asyncio
async def test_emergency_stop_does_not_leave_a_session_lock() -> None:
    engine = AgentEngine.__new__(AgentEngine)
    engine._session_locks = {}
    session = AgentSession(session_id="s-stop", agent_id="a", user_id="u")

    async def collect() -> list[AgentEvent]:
        return [event async for event in engine.run(session, "hello")]

    # The rejection happens before a lock is allocated for this session.
    import app.core.agent_engine as engine_module

    original = engine_module._emergency_stop_active
    engine_module._emergency_stop_active = lambda: True
    try:
        events = await collect()
    finally:
        engine_module._emergency_stop_active = original

    assert events[0].data["emergency_stop"] is True
    assert engine._session_locks == {}


@pytest.mark.asyncio
async def test_consumer_cancellation_marks_session_cancelled(monkeypatch) -> None:
    engine = AgentEngine.__new__(AgentEngine)
    engine._session_locks = {}
    session = AgentSession(session_id="s-cancel", agent_id="a", user_id="u")
    started = asyncio.Event()
    release = asyncio.Event()

    async def run_locked(_session, _message):
        started.set()
        await release.wait()
        yield AgentEvent(type="done", data={})

    monkeypatch.setattr(engine, "_run_locked", run_locked)
    monkeypatch.setattr("app.core.agent_engine._emergency_stop_active", lambda: False)
    monkeypatch.setattr("app.core.agent_engine._observability_sinks", lambda: (None, None))

    task = asyncio.create_task(_collect(engine.run(session, "hello")))
    await started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert session.state_machine.state is TaskState.CANCELLED


@pytest.mark.asyncio
async def test_graceful_shutdown_drains_engine_background_tasks() -> None:
    engine = AgentEngine.__new__(AgentEngine)
    engine._sessions = {}
    engine._background_tasks = set()
    engine._shutdown_event = asyncio.Event()
    engine.resource_tracker = type("Tracker", (), {"cleanup": lambda _self: _noop_async()})()
    completed = asyncio.Event()

    async def background_work() -> None:
        await asyncio.sleep(0)
        completed.set()

    engine._spawn(background_work())
    await engine.graceful_shutdown()

    assert completed.is_set()
    assert engine._background_tasks == set()


@pytest.mark.asyncio
async def test_closing_session_unblocks_permission_wait() -> None:
    engine = AgentEngine.__new__(AgentEngine)
    engine.permission_timeout_seconds = 30.0
    engine._sessions = {}
    engine._session_locks = {}
    engine._session_order = []
    session = AgentSession(session_id="s1", agent_id="a", user_id="u")
    session._pending_permission = {"tool_call_id": "tool-1", "decision": None}
    session._permission_event = asyncio.Event()
    engine._sessions[session.session_id] = session

    task = asyncio.create_task(engine._wait_for_permission(session))
    await asyncio.sleep(0)

    assert engine.close_session(session.session_id) is True
    assert await task == "deny"
    assert session._pending_permission is None
    assert session._permission_event is None


async def _collect(events):
    return [event async for event in events]


async def _noop_async() -> None:
    return None

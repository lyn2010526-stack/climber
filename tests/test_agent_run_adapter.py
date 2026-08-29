"""Contract tests for the AgentEngine unified Run adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from app.core import AgentEvent, AgentEventType, MessageRole
from app.core.agent_run_adapter import AgentEngineRunAdapter
from app.core.run_protocol import (
    ExecutionTokenConflictError,
    InMemoryRunStore,
    MessageEnvelope,
    ResumeRun,
    RunRecord,
    RunStateConflictError,
    RunStatus,
    StartRun,
)


class _FakeSession:
    def __init__(self) -> None:
        self.session_id = "session-1"
        self.user_id = "user-1"
        self.agent_id = "agent-1"
        self.current_turn_id: str | None = None
        self.messages: list[dict[str, Any]] = []
        self.stop_called = False

    def stop(self) -> None:
        self.stop_called = True


class _FakeEngine:
    def __init__(self, events: list[AgentEvent]) -> None:
        self._sessions: dict[str, _FakeSession] = {}
        self._session_locks: dict[str, Any] = {}
        self._events = events
        self.calls: list[dict[str, Any]] = []
        self._checkpoints = SimpleNamespace()

    def add_session(self, session: _FakeSession) -> None:
        self._sessions[session.session_id] = session

    def get_session(self, session_id: str) -> _FakeSession | None:
        return self._sessions.get(session_id)

    def get_session_lock(self, session_id: str) -> Any:
        return self._session_locks.get(session_id)

    async def run(
        self,
        session: _FakeSession,
        message: str,
        *,
        run_id: str | None = None,
        trace_id: str | None = None,
    ):
        self.calls.append(
            {
                "session_id": session.session_id,
                "message": message,
                "run_id": run_id,
                "trace_id": trace_id,
            }
        )
        session.current_turn_id = run_id
        session.messages.append({"role": MessageRole.USER, "content": message})
        for event in self._events:
            yield event


def _start_command() -> StartRun:
    return StartRun(
        session_id="session-1",
        user_id="user-1",
        agent_id="agent-1",
        trace_id="trace-1",
        message=MessageEnvelope(
            message_id="message-1",
            run_id="pending",
            session_id="session-1",
            role=MessageRole.USER,
            content="hello",
            created_at=datetime.now(UTC),
        ),
    )


def _adapter(*events: AgentEvent) -> tuple[AgentEngineRunAdapter, _FakeEngine, InMemoryRunStore]:
    engine = _FakeEngine(list(events))
    engine.add_session(_FakeSession())
    store = InMemoryRunStore()
    return AgentEngineRunAdapter(engine, store=store), engine, store


@pytest.mark.asyncio
async def test_start_and_stream_persist_agent_events_with_run_identity():
    adapter, engine, store = _adapter(
        AgentEvent(type=AgentEventType.THINKING, data={"iteration": 1}),
        AgentEvent(type=AgentEventType.TEXT, data={"content": "hello"}),
        AgentEvent(type=AgentEventType.CHECKPOINT, data={"iteration": 1}),
        AgentEvent(type=AgentEventType.DONE, data={"status": "completed", "content": "hello"}),
    )

    handle = await adapter.start(_start_command())
    events = [event async for event in adapter.stream(handle)]
    run = await store.require(handle.run_id)
    replay = await adapter.replay(handle.run_id)

    assert handle.status is RunStatus.RUNNING
    assert run.status is RunStatus.COMPLETED
    assert run.trace_id == "trace-1"
    assert [event.event_type for event in events] == [
        "thinking",
        "text",
        "checkpoint",
        "done",
    ]
    assert [event.sequence for event in events] == [1, 2, 3, 4]
    assert [event.event_id for event in replay.events] == [event.event_id for event in events]
    assert replay.events[2].checkpoint_id == run.checkpoint_id
    assert engine.calls == [
        {
            "session_id": "session-1",
            "message": "hello",
            "run_id": handle.run_id,
            "trace_id": "trace-1",
        }
    ]


@pytest.mark.asyncio
async def test_start_rejects_a_second_active_run_for_the_same_session():
    adapter, _, _ = _adapter(AgentEvent(type=AgentEventType.DONE, data={"status": "completed"}))

    await adapter.start(_start_command())

    with pytest.raises(RunStateConflictError) as error:
        await adapter.start(_start_command())

    assert error.value.code == "run_conflict"


@pytest.mark.asyncio
async def test_error_event_fails_the_run_with_structured_error():
    adapter, _, store = _adapter(AgentEvent(type=AgentEventType.ERROR, data={"error": "provider failed"}))

    handle = await adapter.start(_start_command())
    events = [event async for event in adapter.stream(handle)]
    run = await store.require(handle.run_id)

    assert events[0].event_type == "error"
    assert run.status is RunStatus.FAILED
    assert run.error == {"code": "agent_error", "message": "provider failed"}
    assert run.error_message == "provider failed"


@pytest.mark.asyncio
async def test_stream_fences_a_stale_execution_handle():
    adapter, _, store = _adapter(AgentEvent(type=AgentEventType.DONE, data={"status": "completed"}))

    handle = await adapter.start(_start_command())
    current = await store.require(handle.run_id)
    stale = handle.__class__(
        run_id=handle.run_id,
        session_id=handle.session_id,
        execution_token=current.execution_token - 1,
    )

    with pytest.raises(ExecutionTokenConflictError):
        _ = [event async for event in adapter.stream(stale)]


@pytest.mark.asyncio
async def test_cancel_without_an_active_stream_fences_future_business_events():
    adapter, engine, _ = _adapter(AgentEvent(type=AgentEventType.DONE, data={"status": "completed"}))

    handle = await adapter.start(_start_command())
    cancelled = await adapter.cancel(handle.run_id, actor_id="user-1")

    assert cancelled.status is RunStatus.CANCELLED
    assert cancelled.metadata["termination"] == {"reason": "cancelled_user"}
    assert engine._sessions["session-1"].stop_called is True
    with pytest.raises(RunStateConflictError):
        _ = [event async for event in adapter.stream(handle)]


@pytest.mark.asyncio
async def test_start_recovers_stale_active_run_instead_of_blocking_session():
    adapter, _, store = _adapter(
        AgentEvent(type=AgentEventType.TEXT, data={"content": "after restart"}),
        AgentEvent(type=AgentEventType.DONE, data={"status": "completed"}),
    )

    crashed = await store.create(
        RunRecord(run_id="stale-run", session_id="session-1", user_id="user-1")
    )
    await store.transition("stale-run", RunStatus.PENDING, RunStatus.RUNNING)
    assert crashed is not None

    handle = await adapter.start(_start_command())
    events = [event async for event in adapter.stream(handle)]

    stale = await store.require("stale-run")
    new_run = await store.require(handle.run_id)
    assert stale.status is RunStatus.FAILED
    assert stale.error == {
        "code": "stale_run",
        "message": "Run had no live executor and was marked failed",
    }
    assert stale.metadata["termination"] == {
        "reason": "interrupted_by_recovery",
        "detail": "stale_run",
    }
    assert new_run.status is RunStatus.COMPLETED
    assert [event.event_type for event in events] == ["text", "done"]


@pytest.mark.asyncio
async def test_cancel_race_surfaces_stopped_event_without_error():
    adapter, _, store = _adapter(
        AgentEvent(type=AgentEventType.TEXT, data={"content": "chunk"}),
        AgentEvent(type=AgentEventType.DONE, data={"status": "completed"}),
    )

    handle = await adapter.start(_start_command())
    stream = adapter.stream(handle)
    first = await stream.__anext__()
    assert first.event_type == "text"

    await adapter.cancel(handle.run_id, actor_id="user-1")

    remaining = [event async for event in stream]
    run = await store.require(handle.run_id)

    assert [event.event_type for event in remaining] == ["stopped"]
    assert remaining[0].data == {"reason": "user_requested"}
    assert remaining[0].sequence is None
    assert run.status is RunStatus.CANCELLED

    replay = await adapter.replay(handle.run_id)
    assert [event.event_type for event in replay.events] == ["text"]


@pytest.mark.asyncio
async def test_resume_with_mismatched_session_or_user_raises_forbidden():
    adapter, _, _ = _adapter(AgentEvent(type=AgentEventType.DONE, data={"status": "completed"}))

    handle = await adapter.start(_start_command())
    await adapter.cancel(handle.run_id, actor_id="user-1")

    wrong_session = ResumeRun(
        run_id=handle.run_id,
        session_id="other-session",
        user_id="user-1",
        execution_token=handle.execution_token,
    )
    wrong_user = ResumeRun(
        run_id=handle.run_id,
        session_id="session-1",
        user_id="intruder",
        execution_token=handle.execution_token,
    )

    for command in (wrong_session, wrong_user):
        with pytest.raises(RunStateConflictError) as error:
            await adapter.resume(command)
        assert error.value.code == "forbidden"


@pytest.mark.asyncio
async def test_cancel_allows_anonymous_run_without_ownership_record():
    adapter, engine, store = _adapter()

    second_session = _FakeSession()
    second_session.session_id = "session-2"
    second_session.user_id = ""
    engine.add_session(second_session)

    created = await store.create(
        RunRecord(run_id="anon-run", session_id="session-2", user_id="")
    )
    await store.transition("anon-run", RunStatus.PENDING, RunStatus.RUNNING)
    assert created is not None

    cancelled = await adapter.cancel("anon-run", actor_id="anyone")
    assert cancelled.status is RunStatus.CANCELLED

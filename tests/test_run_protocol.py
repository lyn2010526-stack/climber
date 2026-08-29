"""Tests for the first unified Run protocol slice."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.core import MessageRole
from app.core.run_protocol import (
    EventVocabularyError,
    InMemoryRunStore,
    MessageEnvelope,
    RunEvent,
    RunRecord,
    RunStateConflictError,
    RunStatus,
)


def make_run(*, run_id: str = "run-1") -> RunRecord:
    return RunRecord(
        run_id=run_id,
        session_id="session-1",
        user_id="user-1",
        kind="agent_chat",
    )


def make_event(
    *,
    event_id: str = "event-1",
    sequence: int | None = None,
    event_type: str = "text",
    data: dict[str, object] | None = None,
) -> RunEvent:
    return RunEvent(
        event_id=event_id,
        run_id="run-1",
        sequence=sequence,
        event_type=event_type,
        data=data or {"content": "hello"},
        created_at=datetime.now(UTC),
    )


def test_run_record_defaults_to_pending_with_initial_execution_token():
    run = make_run()

    assert run.status is RunStatus.PENDING
    assert run.execution_token == 0
    assert run.last_sequence == 0
    assert run.trace_id is None


@pytest.mark.asyncio
async def test_run_store_transitions_pending_to_running_and_increments_token():
    store = InMemoryRunStore()
    await store.create(make_run())

    running = await store.transition("run-1", RunStatus.PENDING, RunStatus.RUNNING)

    assert running.status is RunStatus.RUNNING
    assert running.execution_token == 1
    assert running.started_at is not None


@pytest.mark.asyncio
async def test_run_store_rejects_invalid_transition_with_structured_error():
    store = InMemoryRunStore()
    await store.create(make_run())

    with pytest.raises(RunStateConflictError) as error:
        await store.transition("run-1", RunStatus.PENDING, RunStatus.COMPLETED)

    assert error.value.code == "run_state_conflict"
    assert error.value.run_id == "run-1"
    assert error.value.current is RunStatus.PENDING
    assert error.value.target is RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_run_store_assigns_contiguous_event_sequences_and_replays_after_cursor():
    store = InMemoryRunStore()
    await store.create(make_run())

    first = await store.append_event(make_event())
    second = await store.append_event(make_event(event_id="event-2"))
    page = await store.list_events("run-1", after=1, limit=10)

    assert (first.sequence, second.sequence) == (1, 2)
    assert [event.event_id for event in page.events] == ["event-2"]
    assert page.oldest_sequence == 1
    assert page.latest_sequence == 2
    assert page.has_gap is False


@pytest.mark.asyncio
async def test_run_store_repeated_event_id_is_idempotent():
    store = InMemoryRunStore()
    await store.create(make_run())

    first = await store.append_event(make_event())
    repeated = await store.append_event(make_event(data={"content": "changed"}))
    page = await store.list_events("run-1", after=0, limit=10)

    assert repeated == first
    assert len(page.events) == 1
    assert page.events[0].data == {"content": "hello"}


@pytest.mark.asyncio
async def test_run_store_fences_events_after_terminal_transition():
    store = InMemoryRunStore()
    await store.create(make_run())
    await store.transition("run-1", RunStatus.PENDING, RunStatus.RUNNING)
    await store.transition("run-1", RunStatus.RUNNING, RunStatus.COMPLETED)

    with pytest.raises(RunStateConflictError) as error:
        await store.append_event(make_event(event_id="late-event"))

    assert error.value.code == "run_state_conflict"
    assert error.value.current is RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_run_store_fences_stale_execution_token():
    store = InMemoryRunStore()
    await store.create(make_run())
    running = await store.transition("run-1", RunStatus.PENDING, RunStatus.RUNNING)

    with pytest.raises(RunStateConflictError) as error:
        await store.append_event(make_event(), execution_token=running.execution_token - 1)

    assert error.value.code == "execution_token_conflict"


@pytest.mark.asyncio
async def test_run_store_reports_gap_when_cursor_precedes_retained_window():
    store = InMemoryRunStore(event_capacity=2)
    await store.create(make_run())
    await store.transition("run-1", RunStatus.PENDING, RunStatus.RUNNING)

    for index in range(3):
        await store.append_event(make_event(event_id=f"event-{index + 1}"))

    page = await store.list_events("run-1", after=0, limit=10)

    assert [event.sequence for event in page.events] == [2, 3]
    assert page.oldest_sequence == 2
    assert page.has_gap is True


def test_message_envelope_round_trips_standard_and_tool_fields():
    created_at = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
    message = MessageEnvelope(
        message_id="message-1",
        run_id="run-1",
        session_id="session-1",
        role=MessageRole.TOOL,
        content={"ok": True},
        created_at=created_at,
        tool_call_id="call-1",
        tool_name="read_file",
        provider="openai",
        model_id="gpt-test",
        raw_payload_ref="payload-1",
    )

    restored = MessageEnvelope.from_dict(message.to_dict())

    assert restored == message


@pytest.mark.asyncio
async def test_run_store_allows_abandoning_pending_and_paused_runs():
    store = InMemoryRunStore()
    await store.create(make_run(run_id="run-pending"))
    await store.create(make_run(run_id="run-paused"))
    await store.transition("run-paused", RunStatus.PENDING, RunStatus.RUNNING)
    await store.transition("run-paused", RunStatus.RUNNING, RunStatus.PAUSED)

    failed = await store.transition("run-pending", RunStatus.PENDING, RunStatus.FAILED)
    cancelled = await store.transition("run-paused", RunStatus.PAUSED, RunStatus.CANCELLED)

    assert failed.status is RunStatus.FAILED
    assert failed.completed_at is not None
    assert cancelled.status is RunStatus.CANCELLED
    assert cancelled.completed_at is not None


@pytest.mark.asyncio
async def test_find_active_for_session_returns_latest_active_run():
    store = InMemoryRunStore()
    older = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
    newer = datetime(2026, 8, 28, 13, 0, tzinfo=UTC)
    await store.create(RunRecord(run_id="run-old", session_id="session-1", user_id="user-1", created_at=older))
    await store.create(RunRecord(run_id="run-new", session_id="session-1", user_id="user-1", created_at=newer))

    active = await store.find_active_for_session("session-1")

    assert active is not None
    assert active.run_id == "run-new"


@pytest.mark.asyncio
async def test_append_rejects_unknown_event_type():
    store = InMemoryRunStore()
    await store.create(make_run())

    with pytest.raises(EventVocabularyError) as error:
        await store.append_event(make_event(event_type="legacy_event"))

    assert error.value.code == "event_vocabulary_invalid"
    assert error.value.event_type == "legacy_event"


@pytest.mark.asyncio
async def test_append_accepts_audit_family_events():
    store = InMemoryRunStore()
    await store.create(make_run())

    stored = await store.append_event(make_event(event_id="audit-1", event_type="audit.retry"))

    assert stored.event_type == "audit.retry"


@pytest.mark.asyncio
async def test_list_events_marks_foreign_event_types():
    store = InMemoryRunStore()
    await store.create(make_run())
    await store.append_event(make_event())

    foreign = RunEvent(
        event_id="foreign-1",
        run_id="run-1",
        sequence=2,
        event_type="legacy_event",
        data={},
        created_at=datetime.now(UTC),
    )
    store._events["run-1"].append(foreign)

    page = await store.list_events("run-1")

    assert page.unknown_event_types == ("legacy_event",)
    assert [event.event_id for event in page.events] == ["event-1", "foreign-1"]


@pytest.mark.asyncio
async def test_list_runs_filters_by_session_status_and_paginates():
    store = InMemoryRunStore()
    await store.create(make_run(run_id="run-a"))
    await store.create(make_run(run_id="run-b"))
    await store.create(
        RunRecord(run_id="run-c", session_id="session-2", user_id="user-1", kind="agent_chat")
    )
    await store.transition("run-b", RunStatus.PENDING, RunStatus.RUNNING)
    await store.transition("run-b", RunStatus.RUNNING, RunStatus.COMPLETED)

    page = await store.list_runs(session_id="session-1", limit=10)
    assert [run.run_id for run in page.items] == ["run-b", "run-a"]
    assert page.total == 2

    completed = await store.list_runs(status=RunStatus.COMPLETED)
    assert [run.run_id for run in completed.items] == ["run-b"]

    paged = await store.list_runs(limit=1, offset=1)
    assert len(paged.items) == 1
    assert paged.total == 3


@pytest.mark.asyncio
async def test_list_runs_clamps_limit_and_offset():
    store = InMemoryRunStore()
    await store.create(make_run())
    page = await store.list_runs(limit=9999, offset=-1)
    assert page.limit == 200
    assert page.offset == 0
    assert [run.run_id for run in page.items] == ["run-1"]

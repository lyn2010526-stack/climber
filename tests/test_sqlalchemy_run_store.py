"""Integration tests for the durable SQLAlchemy RunStore."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from app.core.run_protocol import (
    CheckpointScopeMismatchError,
    EventSequenceConflictError,
    EventVocabularyError,
    ExecutionTokenConflictError,
    RunEvent,
    RunRecord,
    RunStateConflictError,
    RunStatus,
)
from app.storage import async_session
from app.storage.database import CheckpointRecord, RunEventRecord
from app.storage.database import Session as SessionModel
from app.storage.run_store import SQLAlchemyRunStore


async def create_session(session_id: str = "session-1") -> None:
    async with async_session() as db:
        db.add(SessionModel(id=session_id, user_id="user-1", title="Run test"))
        await db.commit()


def make_run(*, run_id: str = "run-1") -> RunRecord:
    return RunRecord(
        run_id=run_id,
        session_id="session-1",
        user_id="user-1",
        agent_id="agent-1",
        trace_id="trace-1",
    )


def make_event(*, event_id: str = "event-1", sequence: int | None = None) -> RunEvent:
    from datetime import UTC, datetime

    return RunEvent(
        event_id=event_id,
        run_id="run-1",
        sequence=sequence,
        event_type="text",
        data={"content": "hello"},
        created_at=datetime.now(UTC),
        trace_id="trace-1",
    )


@pytest.mark.asyncio
async def test_sqlalchemy_store_round_trips_run_across_store_instances():
    await create_session()
    store = SQLAlchemyRunStore(session_factory=async_session)

    created = await store.create(make_run())
    loaded = await SQLAlchemyRunStore(session_factory=async_session).get("run-1")

    assert created.run_id == "run-1"
    assert created.kind == "agent_chat"
    assert loaded == created


@pytest.mark.asyncio
async def test_sqlalchemy_store_uses_conditional_transition_and_execution_tokens():
    await create_session()
    store = SQLAlchemyRunStore(session_factory=async_session)
    await store.create(make_run())

    running = await store.transition("run-1", RunStatus.PENDING, RunStatus.RUNNING)
    completed = await store.transition(
        "run-1",
        RunStatus.RUNNING,
        RunStatus.COMPLETED,
        execution_token=running.execution_token,
    )

    assert running.execution_token == 1
    assert completed.status is RunStatus.COMPLETED
    assert completed.completed_at is not None

    resumed = await store.transition(
        "run-1",
        RunStatus.COMPLETED,
        RunStatus.RUNNING,
        execution_token=running.execution_token,
    )

    with pytest.raises(ExecutionTokenConflictError):
        await store.transition(
            "run-1",
            RunStatus.RUNNING,
            RunStatus.COMPLETED,
            execution_token=running.execution_token,
        )

    assert resumed.execution_token == 2


@pytest.mark.asyncio
async def test_sqlalchemy_store_persists_idempotent_events_and_replays_them():
    await create_session()
    store = SQLAlchemyRunStore(session_factory=async_session)
    await store.create(make_run())
    running = await store.transition("run-1", RunStatus.PENDING, RunStatus.RUNNING)

    first = await store.append_event(make_event(), execution_token=running.execution_token)
    repeated = await store.append_event(make_event(), execution_token=running.execution_token)
    page = await SQLAlchemyRunStore(session_factory=async_session).list_events("run-1", after=0, limit=10)

    assert first.sequence == 1
    assert repeated == first
    assert [event.event_id for event in page.events] == ["event-1"]
    assert page.latest_sequence == 1
    assert page.has_gap is False


@pytest.mark.asyncio
async def test_sqlalchemy_store_serializes_concurrent_events_with_contiguous_sequences():
    await create_session()
    store = SQLAlchemyRunStore(session_factory=async_session)
    await store.create(make_run())
    running = await store.transition("run-1", RunStatus.PENDING, RunStatus.RUNNING)

    events = [make_event(event_id=f"event-{index}") for index in range(1, 5)]
    results = await asyncio.gather(
        *(store.append_event(event, execution_token=running.execution_token) for event in events),
        return_exceptions=True,
    )
    page = await store.list_events("run-1", after=0, limit=10)

    failures = [result for result in results if isinstance(result, Exception)]
    assert failures == []
    assert sorted(event.sequence for event in results) == [1, 2, 3, 4]
    assert [event.sequence for event in page.events] == [1, 2, 3, 4]


@pytest.mark.asyncio
async def test_sqlalchemy_store_paginates_with_gap_metadata_and_round_trips_errors():
    await create_session()
    store = SQLAlchemyRunStore(session_factory=async_session)
    created = await store.create(make_run())
    failed = await store.transition(
        "run-1",
        RunStatus.PENDING,
        RunStatus.RUNNING,
        values={"metadata": {"source": "test"}},
    )
    failed = await store.transition(
        "run-1",
        RunStatus.RUNNING,
        RunStatus.FAILED,
        values={"error": {"code": "provider_timeout", "retryable": True}, "error_message": "timed out"},
        execution_token=failed.execution_token,
    )
    assert failed.error == {"code": "provider_timeout", "retryable": True}
    assert failed.metadata == {"source": "test"}

    await store.transition("run-1", RunStatus.FAILED, RunStatus.RUNNING, execution_token=failed.execution_token)
    running = await store.require("run-1")
    for index in range(3):
        await store.append_event(make_event(event_id=f"page-{index}"), execution_token=running.execution_token)

    first_page = await store.list_events("run-1", after=0, limit=2)
    second_page = await store.list_events("run-1", after=first_page.next_after or 0, limit=2)

    assert created.metadata == {}
    assert first_page.has_more is True
    assert first_page.next_after == 2
    assert [event.sequence for event in second_page.events] == [3]
    assert second_page.has_more is False


@pytest.mark.asyncio
async def test_sqlalchemy_store_allows_audit_events_after_terminal_state():
    await create_session()
    store = SQLAlchemyRunStore(session_factory=async_session)
    await store.create(make_run())
    running = await store.transition("run-1", RunStatus.PENDING, RunStatus.RUNNING)
    await store.transition("run-1", RunStatus.RUNNING, RunStatus.COMPLETED, execution_token=running.execution_token)

    audit = await store.append_event(
        RunEvent(
            event_id="audit-1",
            run_id="run-1",
            sequence=None,
            event_type="audit.completed",
            data={"actor": "system"},
            created_at=make_event().created_at,
        ),
        execution_token=running.execution_token,
    )

    assert audit.sequence == 1


@pytest.mark.asyncio
async def test_sqlalchemy_store_rejects_checkpoint_from_another_session_or_run():
    await create_session("session-1")
    await create_session("session-2")
    store = SQLAlchemyRunStore(session_factory=async_session)
    await store.create(make_run())
    running = await store.transition("run-1", RunStatus.PENDING, RunStatus.RUNNING)

    async with async_session() as db:
        db.add(
            CheckpointRecord(
                id="checkpoint-other",
                session_id="session-2",
                thread_id="run-2",
                messages="[]",
                iteration=1,
                status="processing",
                tool_results="[]",
                metadata_="{}",
            )
        )
        await db.commit()

    with pytest.raises(CheckpointScopeMismatchError):
        await store.attach_checkpoint(
            "run-1",
            "checkpoint-other",
            iteration=1,
            execution_token=running.execution_token,
        )


@pytest.mark.asyncio
async def test_sqlalchemy_store_rejects_sequence_conflicts_and_terminal_business_events():
    await create_session()
    store = SQLAlchemyRunStore(session_factory=async_session)
    await store.create(make_run())
    running = await store.transition("run-1", RunStatus.PENDING, RunStatus.RUNNING)
    await store.append_event(make_event(), execution_token=running.execution_token)

    with pytest.raises(EventSequenceConflictError):
        await store.append_event(make_event(event_id="event-2", sequence=3), execution_token=running.execution_token)

    await store.transition(
        "run-1",
        RunStatus.RUNNING,
        RunStatus.COMPLETED,
        execution_token=running.execution_token,
    )
    with pytest.raises(RunStateConflictError):
        await store.append_event(make_event(event_id="late"), execution_token=running.execution_token)


@pytest.mark.asyncio
async def test_sqlalchemy_store_checkpoint_attachment_updates_run_metadata():
    await create_session()
    store = SQLAlchemyRunStore(session_factory=async_session)
    await store.create(make_run())
    running = await store.transition("run-1", RunStatus.PENDING, RunStatus.RUNNING)

    await store.attach_checkpoint("run-1", "checkpoint-1", iteration=2, execution_token=running.execution_token)
    loaded = await store.require("run-1")

    assert loaded.checkpoint_id == "checkpoint-1"
    assert loaded.metadata["checkpoint_iteration"] == 2


@pytest.mark.asyncio
async def test_sqlalchemy_store_rejects_unknown_event_type_on_append():
    await create_session()
    store = SQLAlchemyRunStore(session_factory=async_session)
    await store.create(make_run())

    with pytest.raises(EventVocabularyError) as error:
        await store.append_event(
            RunEvent(
                event_id="legacy-1",
                run_id="run-1",
                sequence=None,
                event_type="legacy_event",
                data={},
                created_at=datetime.now(UTC),
            )
        )

    assert error.value.code == "event_vocabulary_invalid"


@pytest.mark.asyncio
async def test_sqlalchemy_store_marks_foreign_event_types_on_read():
    await create_session()
    store = SQLAlchemyRunStore(session_factory=async_session)
    await store.create(make_run())
    await store.append_event(make_event())

    async with async_session() as db:
        db.add(
            RunEventRecord(
                id="row-legacy",
                run_id="run-1",
                event_id="legacy-1",
                sequence=2,
                event_type="legacy_event",
                data={},
                created_at=datetime.now(UTC).replace(tzinfo=None),
                execution_token=0,
            )
        )
        await db.commit()

    page = await store.list_events("run-1")

    assert page.unknown_event_types == ("legacy_event",)
    assert [event.event_type for event in page.events] == ["text", "legacy_event"]


@pytest.mark.asyncio
async def test_sqlalchemy_store_lists_runs_with_filters_and_pagination():
    await create_session()
    await create_session("session-2")
    store = SQLAlchemyRunStore(session_factory=async_session)
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

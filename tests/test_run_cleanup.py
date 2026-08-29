"""Tests for the background run/payload cleanup sweepers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.core.raw_payload import RawPayloadSnapshot
from app.core.run_cleanup import cleanup_expired_raw_payloads, cleanup_stale_runs
from app.core.run_protocol import InMemoryRunStore, RunRecord, RunStatus
from app.storage import async_session
from app.storage.database import Session as SessionModel
from app.storage.run_store import SQLAlchemyRunStore


def make_run(
    *,
    run_id: str = "run-1",
    status: RunStatus = RunStatus.PENDING,
    created_at: datetime | None = None,
    started_at: datetime | None = None,
) -> RunRecord:
    return RunRecord(
        run_id=run_id,
        session_id="session-1",
        user_id="user-1",
        kind="agent_chat",
        status=status,
        created_at=created_at or datetime.now(UTC),
        started_at=started_at,
    )


@pytest.mark.asyncio
async def test_cleanup_stale_runs_marks_old_active_runs_failed():
    now = datetime.now(UTC)
    store = InMemoryRunStore()
    await store.create(make_run(run_id="old-pending", created_at=now - timedelta(hours=3)))
    await store.create(make_run(run_id="old-running", status=RunStatus.RUNNING, started_at=now - timedelta(hours=2)))
    await store.create(make_run(run_id="fresh-running", status=RunStatus.RUNNING, started_at=now - timedelta(minutes=5)))
    await store.create(
        make_run(run_id="terminal", status=RunStatus.COMPLETED, started_at=now - timedelta(hours=5))
    )

    swept = await cleanup_stale_runs(store, max_age=timedelta(hours=1), now=now)

    assert swept == 2
    old_pending = await store.require("old-pending")
    assert old_pending.status is RunStatus.FAILED
    assert old_pending.error == {
        "code": "stale_run",
        "message": "Run exceeded its maximum age of 1:00:00 without progressing and was marked failed",
    }
    assert old_pending.metadata["termination"]["reason"] == "interrupted_by_recovery"
    old_running = await store.require("old-running")
    assert old_running.status is RunStatus.FAILED
    fresh = await store.require("fresh-running")
    assert fresh.status is RunStatus.RUNNING
    terminal = await store.require("terminal")
    assert terminal.status is RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_cleanup_stale_runs_is_idempotent():
    now = datetime.now(UTC)
    store = InMemoryRunStore()
    await store.create(make_run(run_id="old-pending", created_at=now - timedelta(hours=3)))

    assert await cleanup_stale_runs(store, max_age=timedelta(hours=1), now=now) == 1
    assert await cleanup_stale_runs(store, max_age=timedelta(hours=1), now=now) == 0
    assert (await store.require("old-pending")).status is RunStatus.FAILED


@pytest.mark.asyncio
async def test_cleanup_expired_raw_payloads_deletes_expired_keeps_future_and_standard():
    now = datetime.now(UTC)
    store = SQLAlchemyRunStore(session_factory=async_session)
    async with async_session() as db:
        db.add(SessionModel(id="session-1", user_id="user-1", title="cleanup"))
        await db.commit()

    for rid in ("run-e1", "run-e2", "run-e3"):
        await store.create(RunRecord(run_id=rid, session_id="session-1", user_id="user-1"))

    expired = RawPayloadSnapshot(
        run_id="run-e1",
        message_id=None,
        provider="openai",
        payload_digest="d" * 64,
        expires_at=now - timedelta(days=1),
    )
    future = RawPayloadSnapshot(
        run_id="run-e2",
        message_id=None,
        provider="openai",
        payload_digest="e" * 64,
        expires_at=now + timedelta(days=1),
    )
    standard = RawPayloadSnapshot(
        run_id="run-e3",
        message_id=None,
        provider="openai",
        payload_digest="f" * 64,
        expires_at=None,
    )
    for snapshot in (expired, future, standard):
        await store.save_raw_payload(snapshot)

    deleted = await cleanup_expired_raw_payloads(store, now=now)

    assert deleted == 1
    assert [r.run_id for r in await store.list_raw_payloads("run-e2")] == ["run-e2"]
    assert [r.run_id for r in await store.list_raw_payloads("run-e3")] == ["run-e3"]

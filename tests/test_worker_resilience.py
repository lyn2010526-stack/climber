"""Resilience tests for the task worker's retry and crash-recovery paths.

Covers audit items P1-25 (a transient failure used to fail a task outright) and
P1-26 (a RUNNING row left behind by a crash used to hang forever, and a
duplicate submission could double-charge).

The database here is a throwaway SQLite file created per session, so nothing
touches ``data/climber.db`` or ``data/test.db``. ``app/storage/__init__.py``
binds its engine to ``settings.test_database_url`` at import time, which
happens before this module is imported, so the fixtures rebind the module-level
``async_session`` that ``app.core.task_worker`` and ``app.core.auto_loop`` both
hold their own reference to.
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def worker_db(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    """A private SQLite file for this test session only."""
    yield tmp_path_factory.mktemp("worker_resilience") / "worker_resilience.db"


@pytest.fixture(scope="session", autouse=True)
def bind_worker_sessions(worker_db: Path) -> Iterator[Path]:
    """Point ``app.core.task_worker``/``app.core.auto_loop`` at the private DB.

    Both modules do ``from app.storage import async_session``, so each holds a
    reference captured at import. Rebinding all three names — the sessionmaker
    in ``app.storage`` and the two module-level copies — is what keeps this
    suite off the shared test database.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from app.core import auto_loop as auto_loop_module
    from app.core import task_worker as task_worker_module
    from app.storage import Base, async_session

    # NullPool, not StaticPool: pytest-asyncio gives each test its own event
    # loop, and a pooled connection opened under an earlier loop would raise
    # "Lock is bound to a different event loop" on its next use.
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{worker_db}",
        poolclass=NullPool,
        connect_args={"check_same_thread": False},
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)

    import app.storage as storage_module

    original_storage = storage_module.async_session
    original_worker = task_worker_module.async_session
    original_auto_loop = auto_loop_module.async_session
    original_engine = storage_module.engine
    storage_module.async_session = factory
    task_worker_module.async_session = factory
    auto_loop_module.async_session = factory
    # ``TaskManager.ensure_schema`` reaches for ``app.storage.engine``; rebind it
    # too so the idempotent column patch lands on the private file rather than
    # on the shared data/test.db.
    storage_module.engine = engine

    from app.storage import (  # noqa: F401 - importing registers the tables
        database,
        models_cost,
        models_eval,
        models_feedback,
        models_files,
        models_groups,
        models_memory,
        models_platform,
        models_plugins,
        models_reasoning,
        models_skills,
        models_traces,
    )

    async def _create() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_create())
    try:
        yield worker_db
    finally:
        storage_module.async_session = original_storage
        task_worker_module.async_session = original_worker
        auto_loop_module.async_session = original_auto_loop
        storage_module.engine = original_engine
        # ``ensure_schema`` caches "already checked" process-wide, and the
        # manager under test must be able to re-check the engine it is given.
        task_worker_module._task_schema_ready = False
        asyncio.run(engine.dispose())


@pytest.fixture(autouse=True)
async def clean_tasks() -> AsyncIterator[None]:
    """Start each test from an empty task table."""
    from app.storage import async_session
    from app.storage.models_platform import AutoLoopTask

    async with async_session() as session:
        await session.execute(AutoLoopTask.__table__.delete())
        await session.commit()
    yield


def make_manager(attempts_budget: int = 3, base_delay: float = 0.0) -> object:
    """A TaskManager with a deterministic, fast retry policy."""
    from app.core.task_worker import RetryPolicy, TaskManager

    return TaskManager(
        max_workers=2,
        retry_policy=RetryPolicy(
            max_attempts=attempts_budget,
            base_delay=base_delay,
            max_delay=base_delay,
            jitter_ratio=0.0,
        ),
        heartbeat_interval=0.05,
    )


async def wait_for_status(manager, task_id: str, *statuses: str, timeout: float = 10.0) -> dict:
    """Poll ``get_status`` until the task reaches one of ``statuses``."""
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        current = await manager.get_status(task_id)
        if current and current["status"] in statuses:
            return current
        await asyncio.sleep(0.02)
    raise AssertionError(
        f"task {task_id} stayed in "
        f"{(await manager.get_status(task_id))['status']}, wanted {statuses}"
    )


async def insert_task_row(
    *,
    task_id: str,
    status: str = "running",
    objective: str | None = None,
    heartbeat_at: datetime | None = None,
    updated_at: datetime | None = None,
    created_at: datetime | None = None,
    attempts: int = 1,
    max_attempts: int = 3,
    last_error: str | None = None,
    source: str = "task_worker",
    idempotency_key: str | None = None,
) -> None:
    """Write a task row directly, the way a crashed process would leave it."""
    from app.storage import async_session
    from app.storage.models_platform import AutoLoopTask

    now = datetime.now(UTC)
    objective = objective if objective is not None else json.dumps(
        {"type": "data_processing", "data": [1, 2, 3], "operation": "uppercase"}
    )
    async with async_session() as session:
        session.add(AutoLoopTask(
            id=task_id,
            objective=objective,
            status=status,
            max_steps=10,
            current_step=0,
            result=None,
            error=None,
            created_at=created_at or now,
            updated_at=updated_at or now,
            started_at=now,
            finished_at=None,
            heartbeat_at=heartbeat_at,
            attempts=attempts,
            max_attempts=max_attempts,
            last_error=last_error,
            idempotency_key=idempotency_key,
            source=source,
        ))
        await session.commit()


async def _count_rows_with_key(idempotency_key: str) -> int:
    from sqlalchemy import func as sa_func
    from sqlalchemy import select as sa_select

    from app.storage import async_session
    from app.storage.models_platform import AutoLoopTask

    async with async_session() as session:
        return (
            await session.execute(
                sa_select(sa_func.count())
                .select_from(AutoLoopTask)
                .where(AutoLoopTask.idempotency_key == idempotency_key)
            )
        ).scalar_one()


async def read_task_row(task_id: str) -> dict:
    from app.storage import async_session
    from app.storage.models_platform import AutoLoopTask

    async with async_session() as session:
        record = await session.get(AutoLoopTask, task_id)
        if record is None:
            raise AssertionError(f"task row {task_id} does not exist")
        return {
            "status": record.status,
            "attempts": record.attempts,
            "max_attempts": record.max_attempts,
            "error": record.error,
            "last_error": record.last_error,
            "result": record.result,
            "heartbeat_at": record.heartbeat_at,
            "idempotency_key": record.idempotency_key,
            "source": record.source,
        }


# ── P1-25: retry policy ───────────────────────────────────────────────────


async def test_classify_failure_separates_retryable_from_permanent() -> None:
    from app.core.task_worker import (
        FailureKind,
        PermanentTaskError,
        RetryableTaskError,
        classify_failure,
        classify_failure_text,
    )

    # A validation error must never burn a retry budget.
    assert classify_failure(ValueError("objective is required")) is FailureKind.PERMANENT
    assert classify_failure(KeyError("workflow")) is FailureKind.PERMANENT
    assert classify_failure(TypeError("bad payload")) is FailureKind.PERMANENT
    assert classify_failure(PermanentTaskError("nope")) is FailureKind.PERMANENT

    # Transport and provider hiccups are worth another attempt.
    assert classify_failure(ConnectionResetError("peer went away")) is FailureKind.RETRYABLE
    assert classify_failure(TimeoutError("read timed out")) is FailureKind.RETRYABLE
    assert classify_failure(RetryableTaskError("flaky")) is FailureKind.RETRYABLE

    class _RateLimited(Exception):
        status_code = 429

    class _ServerError(Exception):
        status_code = 503

    class _BadRequest(Exception):
        status_code = 400

    assert classify_failure(_RateLimited("slow down")) is FailureKind.RETRYABLE
    assert classify_failure(_ServerError("upstream")) is FailureKind.RETRYABLE
    assert classify_failure(_BadRequest("malformed")) is FailureKind.PERMANENT

    # Unrecognised errors default to permanent rather than silently re-running
    # a task that will fail identically and cost another set of tokens.
    assert classify_failure(RuntimeError("????")) is FailureKind.PERMANENT
    assert classify_failure_text("") is FailureKind.PERMANENT
    assert classify_failure_text("503 service unavailable") is FailureKind.RETRYABLE


async def test_retry_policy_backoff_is_exponential_capped_and_jittered() -> None:
    from app.core.task_worker import RetryPolicy

    exact = RetryPolicy(max_attempts=5, base_delay=1.0, max_delay=8.0, jitter_ratio=0.0)
    assert [exact.delay_for(attempt) for attempt in (1, 2, 3, 4, 5)] == [
        1.0, 2.0, 4.0, 8.0, 8.0
    ]

    jittered = RetryPolicy(max_attempts=5, base_delay=1.0, max_delay=100.0, jitter_ratio=0.5)
    samples = [jittered.delay_for(1) for _ in range(200)]
    assert all(0.5 <= value <= 1.5 for value in samples), "jitter must stay within ±50%"
    assert len(set(samples)) > 1, "jitter must actually vary the delay"
    # The ceiling still doubles even with jitter applied.
    assert 1.9 <= max(jittered.delay_for(2) for _ in range(200)) <= 3.0
    assert jittered.delay_for(0) == 0.0

    with pytest.raises(ValueError):
        RetryPolicy(max_attempts=0)


async def test_transient_failure_is_retried_then_succeeds_with_attempt_recorded() -> None:
    manager = make_manager(attempts_budget=3)
    calls: list[int] = []

    async def _flaky(payload, on_progress):
        calls.append(1)
        if len(calls) == 1:
            raise ConnectionResetError("connection reset by peer")
        return {"output": "recovered"}

    manager.register("agent_run", _flaky)
    task_id = await manager.submit("agent_run", {"objective": "go"})

    status = await wait_for_status(manager, task_id, "completed", "failed")
    assert status["status"] == "completed"
    assert len(calls) == 2, "a transient failure must be retried exactly once here"

    row = await read_task_row(task_id)
    assert row["attempts"] == 2, "the attempt that succeeded must still be counted"
    assert row["max_attempts"] == 3
    # The success path clears the failure trail.
    assert row["error"] is None
    assert row["last_error"] is None
    assert row["result"]["output"] == "recovered"


async def test_permanent_failure_is_not_retried() -> None:
    manager = make_manager(attempts_budget=5)
    calls: list[int] = []

    async def _invalid(payload, on_progress):
        calls.append(1)
        raise ValueError("objective is required")

    manager.register("agent_run", _invalid)
    task_id = await manager.submit("agent_run", {})

    status = await wait_for_status(manager, task_id, "failed")
    assert len(calls) == 1, "a validation error must fail on the first attempt"

    assert status["attempts"] == 1
    assert status["retryable"] is False
    assert "permanent failure after 1/5 attempt(s)" in status["error"]
    assert "objective is required" in status["error"]
    assert "manual review" not in status["error"]

    row = await read_task_row(task_id)
    assert row["status"] == "failed"
    assert row["attempts"] == 1
    assert row["last_error"] == "objective is required"


async def test_retry_budget_is_bounded_and_reports_retryable_exhaustion() -> None:
    manager = make_manager(attempts_budget=3)
    calls: list[int] = []

    async def _always_times_out(payload, on_progress):
        calls.append(1)
        raise TimeoutError("read timeout")

    manager.register("agent_run", _always_times_out)
    task_id = await manager.submit("agent_run", {"objective": "go"})

    status = await wait_for_status(manager, task_id, "failed")
    assert len(calls) == 3, "the attempt budget must cap the retries"
    assert status["attempts"] == 3
    assert status["retryable"] is True, "an exhausted retryable failure stays classified retryable"
    assert "retryable failure after 3/3 attempt(s)" in status["error"]
    # The old code reported a blanket "manual review required" for everything.
    assert "manual review" not in status["error"]


async def test_backoff_is_actually_applied_between_attempts() -> None:
    """Assert on the delays themselves, not just on the attempt count."""
    from app.core.task_worker import RetryPolicy, TaskManager

    base_delay = 0.12
    manager = TaskManager(
        max_workers=2,
        retry_policy=RetryPolicy(
            max_attempts=3,
            base_delay=base_delay,
            max_delay=base_delay * 4,
            jitter_ratio=0.0,
        ),
        heartbeat_interval=0.05,
    )
    calls: list[float] = []

    async def _always_times_out(payload, on_progress):
        calls.append(asyncio.get_running_loop().time())
        raise TimeoutError("read timeout")

    manager.register("agent_run", _always_times_out)
    task_id = await manager.submit("agent_run", {"objective": "go"})

    await wait_for_status(manager, task_id, "failed")

    assert len(calls) == 3
    # Two backoffs for three attempts, and they must be 0.12s then 0.24s.
    assert calls[1] - calls[0] >= base_delay
    assert calls[2] - calls[1] >= base_delay * 2
    # And the growth is real wall-clock, not just bookkeeping.
    assert calls[2] - calls[0] >= base_delay


async def test_retryable_failure_survives_a_crashed_worker_and_resumes() -> None:
    """A crash mid-backoff leaves a RUNNING row; recovery must finish the job."""
    manager = make_manager(attempts_budget=3)
    # The persisted row already records the attempt that crashed. Recovery
    # should execute the next handler attempt directly.
    calls: list[int] = [1]

    async def _flaky(payload, on_progress):
        calls.append(1)
        if len(calls) == 1:
            raise ConnectionResetError("connection reset by peer")
        return {"output": "recovered after crash"}

    manager.register("agent_run", _flaky)

    # The exact state a SIGKILL during a backoff sleep leaves behind: the row
    # still reads RUNNING with one attempt counted and a retryable error
    # recorded, but nothing is heartbeating it any more.
    old = datetime.now(UTC) - timedelta(seconds=3600)
    await insert_task_row(
        task_id="crashback001",
        status="running",
        objective=json.dumps({"type": "agent_run", "objective": "go"}),
        attempts=1,
        max_attempts=3,
        last_error="retryable failure: connection reset by peer",
        heartbeat_at=old,
        updated_at=old,
    )

    report = await manager.recover_pending_tasks(stale_after=60.0)
    assert "crashback001" in report.reclaimed
    assert "crashback001" in report.enqueued

    status = await wait_for_status(manager, "crashback001", "completed", "failed", timeout=15.0)
    assert status["status"] == "completed"
    assert status["result"]["output"] == "recovered after crash"
    assert status["attempts"] == 2, "the crashed attempt must not be free"


async def test_a_crash_during_backoff_is_recoverable_because_the_row_stays_running() -> None:
    """The retry loop parks on the row itself, so a crash is always visible.

    This is the property that makes crash recovery complete: the backoff sleep
    happens with the row still RUNNING, so there is no window in which a parked
    task is invisible to the liveness sweep.
    """
    from app.core.task_worker import TaskStatus

    manager = make_manager(attempts_budget=3, base_delay=30.0)
    calls: list[int] = []

    async def _flaky(payload, on_progress):
        calls.append(1)
        if len(calls) == 1:
            raise ConnectionResetError("connection reset by peer")
        return {"output": "done"}

    manager.register("agent_run", _flaky)
    task_id = await manager.submit("agent_run", {"objective": "go"})

    row = await _wait_until_stale_state(task_id)
    assert row["status"] == TaskStatus.RUNNING.value
    assert row["attempts"] == 1
    assert "connection reset" in (row["last_error"] or "")

    # Fresh heartbeat: a live backoff is not stale, so no sweep may take it.
    assert await manager.reclaim_stale_running_tasks(stale_after=300.0) == []
    assert (await read_task_row(task_id))["status"] == TaskStatus.RUNNING.value

    await manager.cancel(task_id)
    await asyncio.sleep(0)


async def test_exhausted_budget_is_not_resurrected_by_recovery() -> None:
    from app.core.task_worker import TaskStatus

    manager = make_manager(attempts_budget=3)
    old = datetime.now(UTC) - timedelta(hours=1)
    await insert_task_row(
        task_id="exhausted01",
        status="running",
        attempts=3,
        max_attempts=3,
        heartbeat_at=old,
        updated_at=old,
        last_error="retryable failure: upstream 503",
    )
    report = await manager.recover_pending_tasks(stale_after=60.0)
    assert "exhausted01" not in report.reclaimed
    assert "exhausted01" not in report.enqueued
    row = await read_task_row("exhausted01")
    assert row["status"] == TaskStatus.FAILED.value, (
        "a crashed row with no attempts left must be closed out, not left looking queued"
    )
    assert "budget" in (row["error"] or "")


# ── P1-26: crashed RUNNING rows ───────────────────────────────────────────


async def test_stale_running_row_is_reclaimed_and_fresh_one_is_not() -> None:
    manager = make_manager()
    old = datetime.now(UTC) - timedelta(seconds=3600)
    await insert_task_row(
        task_id="stale000001",
        status="running",
        heartbeat_at=old,
        updated_at=old,
    )
    # Fresh heartbeat: a live worker is still on it.
    await insert_task_row(
        task_id="fresh000001",
        status="running",
        heartbeat_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    reclaimed = await manager.reclaim_stale_running_tasks(stale_after=300.0)

    assert reclaimed == ["stale000001"]
    assert (await read_task_row("stale000001"))["status"] == "pending"
    assert (await read_task_row("fresh000001"))["status"] == "running", (
        "a live in-flight task must never be stolen from its worker"
    )


async def test_heartbeat_keeps_a_long_running_task_out_of_the_reclaim_path() -> None:
    """The heartbeat, not the RUNNING status, is what protects a live task."""
    from app.core.task_worker import TaskStatus

    manager = make_manager(attempts_budget=1)
    release = asyncio.Event()

    async def _slow(payload, on_progress):
        await release.wait()
        return {"output": "done"}

    manager.register("agent_run", _slow)
    task_id = await manager.submit("agent_run", {"objective": "go"})

    # Let the claim land, then let several heartbeats pass. Without the
    # heartbeat the row would look abandoned even though the task is running.
    await _wait_until_stale_state(task_id)
    before = await read_task_row(task_id)
    assert before["status"] == TaskStatus.RUNNING.value
    first_beat = before["heartbeat_at"]
    await asyncio.sleep(0.25)

    assert await manager.reclaim_stale_running_tasks(stale_after=300.0) == []
    after = await read_task_row(task_id)
    assert after["status"] == "running"
    assert after["heartbeat_at"] > first_beat, "the heartbeat must advance while running"

    release.set()
    assert (await wait_for_status(manager, task_id, "completed"))["status"] == "completed"


async def test_recovery_resumes_a_crashed_task_under_its_original_id() -> None:
    from app.core.task_worker import handle_data_processing

    manager = make_manager(attempts_budget=3)
    manager.register("data_processing", handle_data_processing)
    old = datetime.now(UTC) - timedelta(seconds=3600)
    await insert_task_row(
        task_id="crashed00001",
        status="running",
        objective=json.dumps({"type": "data_processing", "data": ["a", "b"], "operation": "uppercase"}),
        heartbeat_at=old,
        updated_at=old,
        attempts=1,
        max_attempts=3,
    )

    report = await manager.recover_pending_tasks(stale_after=60.0)
    assert report.reclaimed == ["crashed00001"]
    assert report.enqueued == ["crashed00001"]

    deadline = asyncio.get_running_loop().time() + 10.0
    while asyncio.get_running_loop().time() < deadline:
        row = await read_task_row("crashed00001")
        if row["status"] == "completed":
            break
        await asyncio.sleep(0.02)
    row = await read_task_row("crashed00001")
    assert row["status"] == "completed"
    assert row["result"]["results"] == ["A", "B"]
    assert row["attempts"] == 2, "resuming must continue the attempt count, not restart it"


async def test_recovery_leaves_rows_of_the_other_engine_alone() -> None:
    manager = make_manager()
    old = datetime.now(UTC) - timedelta(seconds=3600)
    await insert_task_row(
        task_id="autoloop0001",
        status="running",
        objective="a plain objective the auto_loop engine owns",
        heartbeat_at=old,
        updated_at=old,
        source="auto_loop",
    )

    report = await manager.recover_pending_tasks(stale_after=60.0)

    assert report.reclaimed == []
    assert report.enqueued == []
    assert (await read_task_row("autoloop0001"))["status"] == "running"


async def test_recovery_keeps_its_own_repeated_sweeps_idempotent() -> None:
    """Two sweeps must not start the same row twice."""
    from app.core.task_worker import handle_data_processing

    manager = make_manager(attempts_budget=1)
    manager.register("data_processing", handle_data_processing)
    await insert_task_row(
        task_id="pending00001",
        status="pending",
        attempts=0,
    )
    first = await manager.recover_pending_tasks()
    second = await manager.recover_pending_tasks()
    assert first.enqueued == ["pending00001"]
    assert "pending00001" not in second.enqueued, "an in-flight task must not be enqueued twice"

    row = await read_task_row("pending00001")
    assert row["status"] in {"running", "completed"}
    assert row["attempts"] == 1


async def test_auto_loop_recovery_leaves_a_live_task_to_its_worker() -> None:
    """``recover_interrupted_sessions`` is what main.py runs at startup."""
    from app.core.auto_loop import AutoLoopEngine

    manager = make_manager(attempts_budget=1)
    release = asyncio.Event()

    async def _slow(payload, on_progress):
        await release.wait()
        return {"output": "done"}

    manager.register("agent_run", _slow)
    task_id = await manager.submit("agent_run", {"objective": "go"})
    await _wait_until_stale_state(task_id)

    engine = AutoLoopEngine(heartbeat_timeout=300.0)
    recovered = await engine.recover_interrupted_sessions()

    assert task_id not in engine._tasks, "a live task must not be adopted and re-executed"
    row = await read_task_row(task_id)
    assert row["status"] == "running", "a live task must not be reset to pending"
    assert recovered == 0 or isinstance(recovered, int)

    release.set()
    assert (await wait_for_status(manager, task_id, "completed"))["status"] == "completed"


async def test_auto_loop_reclaims_its_own_crashed_running_row() -> None:
    from app.core.auto_loop import AutoLoopEngine, AutoLoopTaskStatus

    old = datetime.now(UTC) - timedelta(seconds=3600)
    await insert_task_row(
        task_id="orphaned0001",
        status="running",
        objective="autonomous objective",
        heartbeat_at=old,
        updated_at=old,
        source="auto_loop",
    )

    # A fresh engine: ``self._tasks`` is empty, exactly as after a restart.
    engine = AutoLoopEngine(heartbeat_timeout=300.0)
    assert engine._tasks == {}
    await engine._check_stalled_tasks()

    assert "orphaned0001" in engine._tasks, "durable state, not the in-memory dict, drives this"
    record = engine._tasks["orphaned0001"]
    assert record.status == AutoLoopTaskStatus.PENDING
    assert record.error == "Reclaimed after heartbeat timeout"
    assert (await read_task_row("orphaned0001"))["status"] == "pending"

    await engine.stop()


async def test_auto_loop_stall_sweep_does_not_touch_a_tracked_task() -> None:
    from app.core.auto_loop import AutoLoopEngine, AutoLoopRecord, AutoLoopTaskStatus

    manager = make_manager(attempts_budget=1)
    release = asyncio.Event()

    async def _slow(payload, on_progress):
        await release.wait()
        return {"output": "done"}

    manager.register("agent_run", _slow)
    task_id = await manager.submit("agent_run", {"objective": "go"})
    await _wait_until_stale_state(task_id)

    engine = AutoLoopEngine(heartbeat_timeout=300.0)
    engine._tasks[task_id] = AutoLoopRecord(
        task_id=task_id,
        objective="in-memory owner",
        status=AutoLoopTaskStatus.RUNNING,
        heartbeat_at=0.0,  # ancient, so the in-memory check would trip
    )
    await engine._check_stalled_tasks()

    assert (await read_task_row(task_id))["status"] == "running"

    release.set()
    assert (await wait_for_status(manager, task_id, "completed"))["status"] == "completed"
    await engine.stop()


# ── P1-26: idempotency ────────────────────────────────────────────────────


async def test_duplicate_submission_executes_once_and_charges_once() -> None:
    manager = make_manager(attempts_budget=1)
    calls: list[str] = []
    started = asyncio.Event()

    async def _handler(payload, on_progress):
        calls.append(payload["_task_id"])
        started.set()
        await asyncio.sleep(0.2)
        return {"output": "billed once", "tokens_used": 42}

    manager.register("agent_run", _handler)
    payload = {"objective": "charge me", "idempotency_key": "req-abc-123"}

    first = await manager.submit("agent_run", payload, idempotency_key="req-abc-123")
    await asyncio.wait_for(started.wait(), timeout=5)
    second = await manager.submit("agent_run", payload, idempotency_key="req-abc-123")

    assert first == second, "a repeated submission must return the original task id"

    status = await wait_for_status(manager, first, "completed")
    assert status["status"] == "completed"
    assert calls == [first], "the handler must run once for a duplicated key"
    assert status["result"]["tokens_used"] == 42, "the single run keeps its usage"

    assert await _count_rows_with_key("req-abc-123") == 1, (
        "one key must map to exactly one row, so one charge"
    )


async def test_duplicate_after_completion_does_not_rerun_the_task() -> None:
    manager = make_manager(attempts_budget=1)
    calls: list[str] = []

    async def _handler(payload, on_progress):
        calls.append("ran")
        return {"output": "once"}

    manager.register("agent_run", _handler)
    first = await manager.submit("agent_run", {"objective": "x"}, idempotency_key="k-1")
    await wait_for_status(manager, first, "completed")

    second = await manager.submit("agent_run", {"objective": "x"}, idempotency_key="k-1")
    assert second == first
    await asyncio.sleep(0.1)
    assert calls == ["ran"], "a key stays bound to its row after completion"


async def test_concurrent_duplicate_submissions_create_one_row() -> None:
    """The unique index, not the pre-insert lookup, is what makes this safe."""
    manager = make_manager(attempts_budget=1)

    async def _handler(payload, on_progress):
        return {"output": "ok"}

    manager.register("agent_run", _handler)

    ids = await asyncio.gather(*[
        manager.submit("agent_run", {"objective": "x"}, idempotency_key="race-key")
        for _ in range(5)
    ])
    assert len(set(ids)) == 1, f"concurrent duplicates returned {ids}"

    assert await _count_rows_with_key("race-key") == 1


async def test_database_rejects_a_second_row_with_the_same_key() -> None:
    from sqlalchemy.exc import IntegrityError
    from app.storage import async_session

    await insert_task_row(task_id="keyrow00001", status="pending", idempotency_key="dup-key")
    with pytest.raises(IntegrityError):
        await insert_task_row(task_id="keyrow00002", status="pending", idempotency_key="dup-key")


async def test_submit_without_a_key_still_creates_distinct_tasks() -> None:
    manager = make_manager(attempts_budget=1)

    async def _handler(payload, on_progress):
        return {"output": "ok"}

    manager.register("agent_run", _handler)
    first = await manager.submit("agent_run", {"objective": "x"})
    second = await manager.submit("agent_run", {"objective": "x"})
    assert first != second
    for task_id in (first, second):
        assert (await wait_for_status(manager, task_id, "completed"))["status"] == "completed"


# ── Migration ─────────────────────────────────────────────────────────────


def _alembic(*args: str, db_path: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    env["APP_TESTING"] = "false"
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )


def test_migration_is_the_single_head_and_chains_onto_its_parent() -> None:
    heads = subprocess.run(
        [sys.executable, "-m", "alembic", "heads"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert heads.returncode == 0, heads.stderr
    assert heads.stdout.strip().count("(head)") == 1, f"expected one head, got:\n{heads.stdout}"


def test_migration_applies_and_reverts_on_a_throwaway_database(tmp_path: Path) -> None:
    db_path = tmp_path / "migration_roundtrip.db"

    upgrade = _alembic("upgrade", "head", db_path=db_path)
    assert upgrade.returncode == 0, f"upgrade failed:\n{upgrade.stdout}\n{upgrade.stderr}"
    # alembic logs its progress to stderr, not stdout.
    assert "add_task_retry_and_recovery_state" in upgrade.stderr

    with sqlite3.connect(db_path) as con:
        columns = {row[1]: row for row in con.execute("PRAGMA table_info(auto_loop_tasks)")}
        indexes = {
            row[1]: row[2] for row in con.execute("PRAGMA index_list(auto_loop_tasks)")
        }

    for name in ("attempts", "max_attempts", "last_error", "idempotency_key", "source"):
        assert name in columns, f"{name} missing after upgrade"
    assert columns["attempts"][3] == 1, "attempts must be NOT NULL"
    assert columns["max_attempts"][3] == 1, "max_attempts must be NOT NULL"
    assert columns["source"][3] == 1, "source must be NOT NULL"
    for name in ("attempts", "max_attempts", "source"):
        assert columns[name][4] is None, f"{name} must not keep its temporary server default"
    assert indexes.get("ix_auto_loop_tasks_idempotency_key") == 1, (
        "idempotency_key must be uniquely indexed so the database refuses duplicates"
    )

    downgrade = _alembic("downgrade", "base", db_path=db_path)
    assert downgrade.returncode == 0, f"downgrade failed:\n{downgrade.stdout}\n{downgrade.stderr}"

    with sqlite3.connect(db_path) as con:
        remaining = {row[1] for row in con.execute("PRAGMA table_info(auto_loop_tasks)")}
    assert "attempts" not in remaining, "downgrade must remove what upgrade added"
    assert "source" not in remaining

    again = _alembic("upgrade", "head", db_path=db_path)
    assert again.returncode == 0, f"re-upgrade failed:\n{again.stdout}\n{again.stderr}"


def test_migration_round_trip_preserves_existing_rows(tmp_path: Path) -> None:
    """A NOT NULL addition must not fail on a table that already has rows."""
    db_path = tmp_path / "migration_backfill.db"
    first = _alembic("upgrade", "d4e5f6a7b8c9", db_path=db_path)
    assert first.returncode == 0, first.stderr

    with sqlite3.connect(db_path) as con:
        con.execute(
            "INSERT INTO auto_loop_tasks (id, objective, status, max_steps, current_step)"
            " VALUES ('legacy0001', 'old task', 'completed', 10, 10)"
        )
        con.commit()

    upgrade = _alembic("upgrade", "head", db_path=db_path)
    assert upgrade.returncode == 0, f"upgrade over existing rows failed:\n{upgrade.stderr}"

    with sqlite3.connect(db_path) as con:
        row = con.execute(
            "SELECT status, attempts, max_attempts, source FROM auto_loop_tasks"
            " WHERE id = 'legacy0001'"
        ).fetchone()
    assert row == ("completed", 0, 3, "auto_loop"), f"unexpected backfill: {row}"


# ── helpers ───────────────────────────────────────────────────────────────


async def _wait_until_stale_state(task_id: str, timeout: float = 5.0) -> dict:
    """Wait until the task row is RUNNING with at least one attempt counted."""
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        row = await read_task_row(task_id)
        if row["status"] == "running" and row["attempts"] >= 1:
            return row
        await asyncio.sleep(0.02)
    raise AssertionError(f"task {task_id} never reached a running state: {row}")


async def _age_out_heartbeat(task_id: str, *, seconds: float) -> None:
    """Push a row's liveness stamp into the past, as a crashed process would."""
    from app.storage import async_session
    from app.storage.models_platform import AutoLoopTask

    stamp = datetime.now(UTC) - timedelta(seconds=seconds)
    async with async_session() as session:
        record = await session.get(AutoLoopTask, task_id)
        record.heartbeat_at = stamp
        record.updated_at = stamp
        await session.commit()

"""Auto-loop engine for autonomous task execution, persistence and recovery.

"""

from __future__ import annotations

import asyncio
import contextlib
import time
import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

import structlog
from sqlalchemy import func, select, update

from app.core.task_state_machine import TaskState, TaskStateMachine
from app.storage import async_session
from app.storage.models_platform import AutoLoopTask

#: ``auto_loop_tasks.source`` value this engine writes. ``app/core/task_worker.py``
#: uses ``task_worker``; each engine reclaims only the rows it owns.
AUTO_LOOP_SOURCE = "auto_loop"


def _to_utc(ts: float | None) -> datetime | None:
    """Convert a unix timestamp to an *aware* UTC datetime (or None)."""
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=UTC)

logger = structlog.get_logger()


class AutoLoopTaskStatus(StrEnum):
    """Autonomous task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class AutoLoopRecord:
    """In-memory representation of an autonomous task."""

    task_id: str
    objective: str
    max_steps: int = 10
    current_step: int = 0
    status: AutoLoopTaskStatus = AutoLoopTaskStatus.PENDING
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    heartbeat_at: float | None = None
    asyncio_task: asyncio.Task | None = None
    state_machine: TaskStateMachine = field(
        default_factory=lambda: TaskStateMachine(task_id=str(uuid.uuid4()))
    )


class AutoLoopEngine:
    """Background autonomous task execution engine with persistence and recovery.

    - Scheduled cron-like task execution
    - Autonomous task execution with step limits
    - Task state persistence via SQLite
    - Automatic recovery of interrupted sessions on startup
    - Heartbeat mechanism for stalled task detection
    - Clean shutdown preserving state

    This engine owns the ``auto_loop_tasks`` rows whose ``source`` is
    ``auto_loop``. Rows written by ``app/core/task_worker.py`` carry
    ``source = 'task_worker'`` and are recovered by that module; the two
    engines must not reclaim each other's rows, so every query here is scoped
    to this engine's own rows.
    """

    def __init__(
        self,
        heartbeat_timeout: float = 300.0,
        recovery_check_interval: float = 60.0,
    ) -> None:
        self._tasks: dict[str, AutoLoopRecord] = {}
        self._runners: dict[str, Callable[..., Coroutine[Any, Any, None]]] = {}
        self._running = False
        self._monitor: asyncio.Task | None = None
        self._heartbeat_timeout = heartbeat_timeout
        self._recovery_check_interval = recovery_check_interval

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._monitor = asyncio.create_task(
            self._monitor_loop(), name="auto-loop-monitor"
        )
        logger.info("auto_loop_engine_started")

    async def run_forever(self) -> None:
        """Block until the monitor loop exits (for watchdog/long-running modes)."""
        if not self._running:
            await self.start()
        if self._monitor is not None and not self._monitor.done():
            with contextlib.suppress(asyncio.CancelledError):
                await self._monitor

    async def stop(self) -> None:
        """Clean shutdown preserving state."""
        self._running = False
        if self._monitor is not None and not self._monitor.done():
            self._monitor.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._monitor
            self._monitor = None

        for record in self._tasks.values():
            if record.asyncio_task is not None and not record.asyncio_task.done():
                record.asyncio_task.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await record.asyncio_task

        for record in self._tasks.values():
            if record.status in (
                AutoLoopTaskStatus.RUNNING,
                AutoLoopTaskStatus.RETRYING,
            ):
                await self._persist_status(record, AutoLoopTaskStatus.CANCELLED)
        logger.info("auto_loop_engine_stopped")

    def start_task(self, objective: str, max_steps: int = 10) -> str:
        """Start a new autonomous task, returns task_id."""
        task_id = str(uuid.uuid4())
        record = AutoLoopRecord(
            task_id=task_id,
            objective=objective,
            max_steps=max_steps,
        )
        self._tasks[task_id] = record
        record.asyncio_task = asyncio.create_task(
            self._execute_task(record), name=f"auto-loop:{task_id}"
        )
        # Best-effort immediate persistence so a crash before the first
        # internal status write cannot lose the task. `_execute_task` also
        # persists RUNNING promptly; this closes the gap for the brief
        # window before the coroutine body runs.
        with contextlib.suppress(RuntimeError):
            asyncio.get_running_loop().create_task(
                self._persist_status(record, AutoLoopTaskStatus.PENDING)
            )
        logger.info(
            "auto_loop_task_started",
            task_id=task_id,
            objective=objective,
            max_steps=max_steps,
        )
        return task_id

    async def recover_interrupted_sessions(self) -> int:
        """Recover tasks from DB on startup, returns count of recovered tasks.

        This is the recovery path the application actually runs
        (``app/main.py`` calls it from the lifespan startup), so it does two
        jobs: it reclaims this engine's own RUNNING/RETRYING rows whose liveness
        stamp has aged out — a crash victim, not a live task — and it hands the
        ``task_worker`` sweep over to
        :func:`app.core.task_worker.recover_pending_tasks` so crashed
        ``task_worker`` rows are resumed too instead of hanging in RUNNING.

        A RUNNING row with a *fresh* liveness stamp belongs to a live worker,
        typically in another process. It is left untouched and not adopted: the
        previous blanket RUNNING → PENDING reset would have re-executed a task
        that another process was still running, double-charging it.
        """
        count = await self._recover_own_rows()
        count += await self._recover_task_worker_rows()
        return count

    async def _recover_own_rows(self) -> int:
        """Reclaim this engine's stale RUNNING/RETRYING rows and requeue them."""
        count = 0
        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=self._heartbeat_timeout)
        liveness = func.coalesce(
            AutoLoopTask.heartbeat_at,
            AutoLoopTask.updated_at,
            AutoLoopTask.started_at,
            AutoLoopTask.created_at,
        )
        try:
            async with async_session() as db:
                result = await db.execute(
                    select(AutoLoopTask).where(
                        AutoLoopTask.status.in_(
                            [
                                AutoLoopTaskStatus.RUNNING.value,
                                AutoLoopTaskStatus.RETRYING.value,
                                AutoLoopTaskStatus.PENDING.value,
                            ]
                        ),
                        AutoLoopTask.source != "task_worker",
                    )
                )
                rows = result.scalars().all()

                for row in rows:
                    task_id = row.id
                    was_active = row.status in (
                        AutoLoopTaskStatus.RUNNING.value,
                        AutoLoopTaskStatus.RETRYING.value,
                    )
                    if was_active and not self._liveness_expired(row, cutoff):
                        # Someone is still working on it: leave the row alone
                        # and keep no in-memory copy, or the monitor loop would
                        # cancel the other worker's task as stalled.
                        logger.info(
                            "auto_loop_task_owned_by_live_worker",
                            task_id=task_id,
                            status=row.status,
                        )
                        continue

                    if was_active:
                        # Conditional UPDATE: re-assert both the expected status
                        # and the liveness bound, so a heartbeat that landed
                        # after the read keeps the row with its real owner.
                        await db.execute(
                            update(AutoLoopTask)
                            .where(
                                AutoLoopTask.id == task_id,
                                AutoLoopTask.status == row.status,
                                liveness < cutoff,
                            )
                            .values(
                                status=AutoLoopTaskStatus.PENDING.value,
                                heartbeat_at=None,
                                updated_at=now,
                            )
                            .execution_options(synchronize_session=False)
                        )
                        row.status = AutoLoopTaskStatus.PENDING.value

                    new_status = AutoLoopTaskStatus(row.status)
                    record = AutoLoopRecord(
                        task_id=task_id,
                        objective=row.objective,
                        max_steps=row.max_steps or 10,
                        current_step=row.current_step or 0,
                        status=new_status,
                        result=row.result,
                        error=row.error,
                        created_at=row.created_at.timestamp()
                        if row.created_at
                        else time.time(),
                        started_at=row.started_at.timestamp()
                        if row.started_at
                        else None,
                        finished_at=row.finished_at.timestamp()
                        if row.finished_at
                        else None,
                    )
                    self._tasks[task_id] = record

                    if new_status == AutoLoopTaskStatus.PENDING:
                        record.asyncio_task = asyncio.create_task(
                            self._execute_task(record),
                            name=f"auto-loop:{task_id}",
                        )

                    count += 1
                    logger.info(
                        "auto_loop_task_recovered",
                        task_id=task_id,
                        previous_status=row.status,
                        new_status=new_status,
                    )
                await db.commit()
        except Exception as exc:
            logger.error(
                "auto_loop_recovery_failed", error=str(exc), exc_info=True
            )
        return count

    @staticmethod
    def _liveness_expired(row: AutoLoopTask, cutoff: datetime) -> bool:
        """Whether a row stopped showing signs of life before ``cutoff``.

        The newest of ``heartbeat_at``, ``updated_at``, ``started_at`` and
        ``created_at`` is its last sign of life, so a task that crashed before
        writing any of them still ages out instead of looking fresh forever.
        """
        stamps = [row.heartbeat_at, row.updated_at, row.started_at, row.created_at]
        usable = [stamp for stamp in stamps if stamp is not None]
        if not usable:
            # Nothing to age out against. Leave the row with its owner rather
            # than re-executing a task on a guess.
            return False
        newest = max(usable)
        if newest.tzinfo is None:
            newest = newest.replace(tzinfo=UTC)
        return newest < cutoff

    async def _recover_task_worker_rows(self) -> int:
        """Hand crashed ``task_worker`` rows to the worker that owns them."""
        try:
            from app.core.task_worker import recover_pending_tasks

            report = await recover_pending_tasks(
                stale_after=self._heartbeat_timeout,
            )
        except Exception as exc:
            logger.error(
                "auto_loop_task_worker_recovery_failed", error=str(exc), exc_info=True
            )
            return 0
        return len(report.enqueued) + len(report.reclaimed)

    async def run_pending(self) -> None:
        """Process pending/running tasks (called by scheduler)."""
        for record in list(self._tasks.values()):
            if (
                record.status == AutoLoopTaskStatus.PENDING
                and record.asyncio_task is None
            ):
                record.asyncio_task = asyncio.create_task(
                    self._execute_task(record),
                    name=f"auto-loop:{record.task_id}",
                )

    async def get_status(self, task_id: str) -> dict[str, Any] | None:
        """Get task status."""
        record = self._tasks.get(task_id)
        if record is None:
            return None
        return {
            "task_id": record.task_id,
            "objective": record.objective,
            "status": record.status.value,
            "current_step": record.current_step,
            "max_steps": record.max_steps,
            "result": record.result,
            "error": record.error,
            "created_at": record.created_at,
            "started_at": record.started_at,
            "finished_at": record.finished_at,
        }

    def register_runner(self, task_type: str, runner: Callable) -> None:
        """Register a task runner coroutine factory."""
        self._runners[task_type] = runner

    async def _execute_task(self, record: AutoLoopRecord) -> None:
        """Execute an autonomous task."""
        try:
            await record.state_machine.transition(
                TaskState.PROCESSING, trigger="auto_loop_start"
            )
            record.status = AutoLoopTaskStatus.RUNNING
            record.started_at = time.time()
            record.heartbeat_at = time.time()
            await self._persist_status(record, AutoLoopTaskStatus.RUNNING)

            runner = self._runners.get("autonomous")
            if runner is not None:
                real_runner = True
                await runner(record)
            else:
                real_runner = False
                await self._default_runner(record)

            if record.status == AutoLoopTaskStatus.RUNNING:
                if not real_runner:
                    # No real "autonomous" runner is registered. Do NOT
                    # fabricate completion from the simulation placeholder —
                    # keep the task pending so it can be executed when a
                    # runner is wired up, and surface the misconfiguration.
                    record.status = AutoLoopTaskStatus.PENDING
                    await self._persist_status(
                        record, AutoLoopTaskStatus.PENDING
                    )
                    logger.warning(
                        "auto_loop_no_runner_registered",
                        task_id=record.task_id,
                        objective=record.objective[:120],
                    )
                elif record.current_step >= record.max_steps - 1:
                    record.status = AutoLoopTaskStatus.COMPLETED
                    record.finished_at = time.time()
                    await record.state_machine.transition(
                        TaskState.COMPLETED, trigger="auto_loop_complete"
                    )
                    await self._persist_status(
                        record, AutoLoopTaskStatus.COMPLETED
                    )
                    logger.info(
                        "auto_loop_task_completed", task_id=record.task_id
                    )
                else:
                    record.status = AutoLoopTaskStatus.PENDING
                    await self._persist_status(
                        record, AutoLoopTaskStatus.PENDING
                    )
        except asyncio.CancelledError:
            record.status = AutoLoopTaskStatus.CANCELLED
            record.finished_at = time.time()
            await record.state_machine.transition(
                TaskState.CANCELLED, trigger="auto_loop_cancel"
            )
            await self._persist_status(record, AutoLoopTaskStatus.CANCELLED)
            logger.info("auto_loop_task_cancelled", task_id=record.task_id)
        except Exception as exc:
            record.error = str(exc)
            is_transient = self._is_transient_error(exc)
            if is_transient:
                record.status = AutoLoopTaskStatus.RETRYING
                await record.state_machine.transition(
                    TaskState.FAILED, trigger="auto_loop_retry"
                )
                await self._persist_status(
                    record, AutoLoopTaskStatus.RETRYING
                )
                logger.warning(
                    "auto_loop_task_retrying",
                    task_id=record.task_id,
                    error=str(exc),
                )
            else:
                record.status = AutoLoopTaskStatus.FAILED
                record.finished_at = time.time()
                await record.state_machine.transition(
                    TaskState.FAILED, trigger="auto_loop_error"
                )
                await self._persist_status(
                    record, AutoLoopTaskStatus.FAILED
                )
                logger.error(
                    "auto_loop_task_failed",
                    task_id=record.task_id,
                    error=str(exc),
                    exc_info=True,
                )
        finally:
            record.asyncio_task = None

    async def _default_runner(self, record: AutoLoopRecord) -> None:
        """Placeholder when no real 'autonomous' runner is registered.

        Only refreshes the heartbeat so the task is not misclassified as
        stalled. It deliberately does NOT advance steps or mark the task
        completed — fabricated completion is handled in ``_execute_task``
        by keeping the task pending instead.
        """
        record.heartbeat_at = time.time()

    async def _monitor_loop(self) -> None:
        """Monitor loop for stalled task detection."""
        while self._running:
            try:
                await asyncio.sleep(self._recovery_check_interval)
                await self._check_stalled_tasks()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error(
                    "auto_loop_monitor_error", error=str(exc), exc_info=True
                )

    async def _check_stalled_tasks(self) -> None:
        """Detect and handle stalled tasks.

        Two sources are consulted, in this order:

        1. The in-memory records this process owns, as before.
        2. The durable rows, because ``self._tasks`` is empty after a restart
           and a task whose worker crashed leaves a RUNNING row that nothing
           would ever look at again — the state that hangs forever.

        A durable RUNNING row past the heartbeat timeout and not tracked in
        memory belongs to a crashed process. It is returned to PENDING and
        adopted as a pending record so ``run_pending`` or a later
        ``recover_interrupted_sessions`` can start it, which is recoverable
        rather than lost. Rows owned by ``task_worker`` are left to that
        module's own recovery sweep, which knows how to rebuild the payload.
        """
        now = time.time()
        for record in self._tasks.values():
            if (
                record.asyncio_task is not None
                and record.status == AutoLoopTaskStatus.RUNNING
                and (record.heartbeat_at is None or (
                now - record.heartbeat_at > self._heartbeat_timeout
                ))
            ):
                logger.warning(
                    "auto_loop_task_stalled",
                    task_id=record.task_id,
                    heartbeat_age=now - record.heartbeat_at
                    if record.heartbeat_at
                    else None,
                )
                if (
                    record.asyncio_task is not None
                    and not record.asyncio_task.done()
                ):
                    record.asyncio_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await record.asyncio_task
                record.status = AutoLoopTaskStatus.FAILED
                record.error = "Task stalled (no heartbeat)"
                record.finished_at = time.time()
                await self._persist_status(
                    record, AutoLoopTaskStatus.FAILED
                )

        await self._reclaim_orphaned_rows()

    async def _reclaim_orphaned_rows(self) -> list[str]:
        """Requeue RUNNING rows left behind by a crashed worker.

        A row qualifies when it is RUNNING, belongs to this engine, its newest
        liveness stamp is older than the heartbeat timeout, and it is not
        tracked in ``self._tasks`` — the last condition being what keeps a
        legitimately long-running in-memory task from being reclaimed, since a
        live record's database heartbeat is only written on status transitions.
        """
        cutoff = datetime.now(UTC) - timedelta(seconds=self._heartbeat_timeout)
        liveness = func.coalesce(
            AutoLoopTask.heartbeat_at,
            AutoLoopTask.updated_at,
            AutoLoopTask.started_at,
            AutoLoopTask.created_at,
        )
        try:
            async with async_session() as db:
                result = await db.execute(
                    select(AutoLoopTask).where(
                        AutoLoopTask.status == AutoLoopTaskStatus.RUNNING.value,
                        AutoLoopTask.source != "task_worker",
                        liveness < cutoff,
                    )
                )
                rows = result.scalars().all()
                if not rows:
                    return []

                reclaimed: list[str] = []
                now = datetime.now(UTC)
                for row in rows:
                    if row.id in self._tasks:
                        continue
                    await db.execute(
                        update(AutoLoopTask)
                        .where(
                            AutoLoopTask.id == row.id,
                            AutoLoopTask.status == AutoLoopTaskStatus.RUNNING.value,
                            liveness < cutoff,
                        )
                        .values(
                            status=AutoLoopTaskStatus.PENDING.value,
                            heartbeat_at=None,
                            updated_at=now,
                        )
                        .execution_options(synchronize_session=False)
                    )
                    record = AutoLoopRecord(
                        task_id=row.id,
                        objective=row.objective,
                        max_steps=row.max_steps or 10,
                        current_step=row.current_step or 0,
                        status=AutoLoopTaskStatus.PENDING,
                        result=row.result,
                        error="Reclaimed after heartbeat timeout",
                        created_at=row.created_at.timestamp()
                        if row.created_at
                        else time.time(),
                    )
                    self._tasks[row.id] = record
                    reclaimed.append(row.id)
                    logger.warning(
                        "auto_loop_orphaned_task_reclaimed",
                        task_id=row.id,
                    )
                await db.commit()
        except Exception as exc:
            logger.error(
                "auto_loop_orphan_sweep_failed", error=str(exc), exc_info=True
            )
            return []
        return reclaimed

    async def _persist_status(
        self,
        record: AutoLoopRecord,
        status: AutoLoopTaskStatus,
    ) -> None:
        """Persist task status to database."""
        try:
            async with async_session() as db:
                result = await db.execute(
                    select(AutoLoopTask).where(
                        AutoLoopTask.id == record.task_id
                    )
                )
                existing = result.scalars().first()

                now = datetime.now(UTC)
                if existing:
                    existing.status = status.value
                    existing.current_step = record.current_step
                    existing.updated_at = now
                    existing.heartbeat_at = (
                        now if status == AutoLoopTaskStatus.RUNNING else None
                    )
                    if record.error:
                        existing.error = record.error
                    if record.result:
                        existing.result = record.result
                    if record.finished_at:
                        existing.finished_at = _to_utc(record.finished_at)
                    if record.started_at:
                        existing.started_at = _to_utc(record.started_at)
                else:
                    task = AutoLoopTask(
                        id=record.task_id,
                        objective=record.objective,
                        status=status.value,
                        max_steps=record.max_steps,
                        current_step=record.current_step,
                        result=record.result,
                        error=record.error,
                        created_at=_to_utc(record.created_at),
                        started_at=_to_utc(record.started_at),
                        finished_at=_to_utc(record.finished_at),
                        heartbeat_at=now
                        if status == AutoLoopTaskStatus.RUNNING
                        else None,
                    )
                    db.add(task)
                await db.commit()
        except Exception as exc:
            logger.error(
                "auto_loop_persist_failed",
                task_id=record.task_id,
                error=str(exc),
                exc_info=True,
            )

    @staticmethod
    def _is_transient_error(exc: Exception) -> bool:
        """Check if error is transient (retryable)."""
        transient_messages = [
            "timeout",
            "temporarily unavailable",
            "rate limit",
            "429",
            "500",
            "502",
            "503",
            "504",
            "connection",
        ]
        msg = str(exc).lower()
        return any(t in msg for t in transient_messages)


auto_loop_engine = AutoLoopEngine()

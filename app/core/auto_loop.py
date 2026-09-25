"""Auto-loop engine for autonomous task execution, persistence and recovery.

"""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import structlog
from sqlalchemy import select, update

from app.core.task_state_machine import TaskState, TaskStateMachine
from app.storage import async_session
from app.storage.models_platform import AutoLoopTask


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
    owner_id: str | None = field(default=None, kw_only=True)
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

        for record in list(self._tasks.values()):
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

    def start_task(self, objective: str, max_steps: int = 10, *, owner_id: str) -> str:
        """Start a new autonomous task, returns task_id."""
        if not owner_id or not owner_id.strip():
            raise ValueError("Task owner is required")
        try:
            envelope = json.loads(objective)
        except (TypeError, ValueError):
            envelope = None
        if isinstance(envelope, dict) and "type" in envelope:
            raise ValueError("JSON objectives with type are reserved for TaskManager")
        task_id = str(uuid.uuid4())
        record = AutoLoopRecord(
            task_id=task_id,
            objective=objective,
            owner_id=owner_id,
            max_steps=max_steps,
        )
        self._tasks[task_id] = record
        record.asyncio_task = asyncio.create_task(
            self._execute_task(record), name=f"auto-loop:{task_id}"
        )
        logger.info(
            "auto_loop_task_started",
            task_id=task_id,
            objective=objective,
            max_steps=max_steps,
        )
        return task_id

    async def recover_interrupted_sessions(self) -> int:
        """Startup-only recovery; resume never-started pending rows under the same ID.

        Interrupted runs have no durable execution checkpoint. Mark them failed
        for manual review; replaying their tools could repeat side effects.
        Deploy one recovery coordinator; this is not a distributed lease.
        """
        count = 0
        pending_records = []
        try:
            async with async_session() as db:
                result = await db.execute(
                    select(AutoLoopTask).where(
                        AutoLoopTask.status.in_(
                            [
                                AutoLoopTaskStatus.RUNNING,
                                AutoLoopTaskStatus.RETRYING,
                                AutoLoopTaskStatus.PENDING,
                            ]
                        )
                    )
                )
                rows = result.scalars().all()

                for row in rows:
                    task_id = row.id
                    previous_status = row.status
                    if task_id in self._tasks:
                        continue
                    # Tasks persisted by TaskManager (task_worker) use a
                    # JSON-serialized objective envelope with a "type" key.
                    # Skip them so AutoLoopEngine does not double-claim rows
                    # owned by the task worker path.
                    try:
                        envelope = json.loads(row.objective or "")
                    except (TypeError, ValueError):
                        envelope = None
                    if isinstance(envelope, dict) and "type" in envelope:
                        continue

                    new_status = AutoLoopTaskStatus.PENDING
                    if (row.status != AutoLoopTaskStatus.PENDING or row.started_at
                            or row.current_step or row.finished_at or row.result is not None or row.error
                            or not row.owner_id or not row.owner_id.strip()):
                        new_status = AutoLoopTaskStatus.FAILED
                        row.status = new_status.value
                        row.error = "Automatic recovery refused: missing owner or prior execution; manual review required"
                        row.finished_at = datetime.now(UTC)
                        row.heartbeat_at = None

                    record = AutoLoopRecord(
                        task_id=task_id,
                        objective=row.objective,
                        owner_id=row.owner_id,
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
                        pending_records.append(record)

                    count += 1
                    logger.info(
                        "auto_loop_task_recovered",
                        task_id=task_id,
                        previous_status=previous_status,
                        new_status=new_status,
                    )
                await db.commit()
                for record in pending_records:
                    record.asyncio_task = asyncio.create_task(
                        self._execute_task(record), name=f"auto-loop:{record.task_id}"
                    )
        except Exception as exc:
            logger.error(
                "auto_loop_recovery_failed", error=type(exc).__name__
            )
        return count

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
            "owner_id": record.owner_id,
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
        record.started_at = time.time()
        record.heartbeat_at = record.started_at
        try:
            claimed = await self._persist_status(record, AutoLoopTaskStatus.RUNNING, claim=True)
        except Exception as exc:
            record.status = AutoLoopTaskStatus.FAILED
            record.error = f"Task claim failed ({type(exc).__name__})"
            record.asyncio_task = None
            logger.error("auto_loop_claim_failed", task_id=record.task_id, error=record.error)
            return
        if not claimed:
            record.asyncio_task = None
            if self._tasks.get(record.task_id) is record:
                self._tasks.pop(record.task_id)
            return
        try:
            await record.state_machine.transition(
                TaskState.PROCESSING, trigger="auto_loop_start"
            )
            record.status = AutoLoopTaskStatus.RUNNING
            runner = self._runners.get("autonomous")
            if runner is None:
                raise RuntimeError("Autonomous runner is not configured")
            await runner(record)

            if record.status == AutoLoopTaskStatus.RUNNING:
                if not isinstance(record.result, dict) or record.result.get("status") != "completed":
                    raise RuntimeError("Runner returned without successful completion")
                record.status = AutoLoopTaskStatus.COMPLETED
                record.finished_at = time.time()
                await record.state_machine.transition(TaskState.COMPLETED, trigger="auto_loop_complete")
                await self._persist_status(record, AutoLoopTaskStatus.COMPLETED)
        except asyncio.CancelledError:
            record.status = AutoLoopTaskStatus.CANCELLED
            record.finished_at = time.time()
            await record.state_machine.transition(
                TaskState.CANCELLED, trigger="auto_loop_cancel"
            )
            await self._persist_status(record, AutoLoopTaskStatus.CANCELLED)
            logger.info("auto_loop_task_cancelled", task_id=record.task_id)
        except Exception as exc:
            record.error = f"Task execution failed ({type(exc).__name__}); manual review required before resubmission"
            record.status = AutoLoopTaskStatus.FAILED
            record.finished_at = time.time()
            await record.state_machine.transition(TaskState.FAILED, trigger="auto_loop_error")
            await self._persist_status(record, AutoLoopTaskStatus.FAILED)
            logger.error("auto_loop_task_failed", task_id=record.task_id, error=record.error)
        finally:
            record.asyncio_task = None

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
        """Detect and handle stalled tasks."""
        now = time.time()
        for record in self._tasks.values():
            if record.status == AutoLoopTaskStatus.RUNNING and (record.heartbeat_at is None or (
                now - record.heartbeat_at > self._heartbeat_timeout
            )):
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

    async def _persist_status(
        self,
        record: AutoLoopRecord,
        status: AutoLoopTaskStatus,
        *,
        claim: bool = False,
    ) -> bool:
        """Persist task status to database."""
        if not record.owner_id:
            raise ValueError("Task owner is required")
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
                    if existing.owner_id != record.owner_id or existing.objective != record.objective:
                        raise ValueError("Task ownership or objective mismatch")
                    if claim:
                        claimed = await db.execute(
                            update(AutoLoopTask).where(
                                AutoLoopTask.id == record.task_id,
                                AutoLoopTask.owner_id == record.owner_id,
                                AutoLoopTask.objective == record.objective,
                                AutoLoopTask.status == AutoLoopTaskStatus.PENDING,
                                AutoLoopTask.started_at.is_(None),
                                AutoLoopTask.finished_at.is_(None),
                                AutoLoopTask.current_step == 0,
                            ).values(status=status.value, started_at=_to_utc(record.started_at), heartbeat_at=now)
                        )
                        await db.commit()
                        return claimed.rowcount == 1
                    existing.status = status.value
                    existing.current_step = record.current_step
                    existing.updated_at = now
                    existing.heartbeat_at = (
                        now if status == AutoLoopTaskStatus.RUNNING else None
                    )
                    if record.error:
                        existing.error = record.error
                    if record.result is not None:
                        existing.result = record.result
                    if record.finished_at:
                        existing.finished_at = _to_utc(record.finished_at)
                    if record.started_at:
                        existing.started_at = _to_utc(record.started_at)
                else:
                    task = AutoLoopTask(
                        id=record.task_id,
                        owner_id=record.owner_id,
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
                return True
        except Exception as exc:
            logger.error(
                "auto_loop_persist_failed",
                task_id=record.task_id,
                error=type(exc).__name__,
            )
            raise

auto_loop_engine = AutoLoopEngine()

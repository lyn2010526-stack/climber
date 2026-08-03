"""Auto-loop engine for autonomous task execution, persistence and recovery.

"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine

import structlog
from sqlalchemy import select, update

from app.core.task_state_machine import TaskState, TaskStateMachine
from app.storage import async_session
from app.storage.models_platform import AutoLoopTask

logger = structlog.get_logger()


class AutoLoopTaskStatus(str, Enum):
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
        # Keep the start task alive so watchdog considers it running
        try:
            await self._monitor
        except asyncio.CancelledError:
            pass

    async def stop(self) -> None:
        """Clean shutdown preserving state."""
        self._running = False
        if self._monitor is not None and not self._monitor.done():
            self._monitor.cancel()
            try:
                await self._monitor
            except (asyncio.CancelledError, Exception):
                pass
            self._monitor = None

        for record in self._tasks.values():
            if record.asyncio_task is not None and not record.asyncio_task.done():
                record.asyncio_task.cancel()
                try:
                    await record.asyncio_task
                except (asyncio.CancelledError, Exception):
                    pass

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
        logger.info(
            "auto_loop_task_started",
            task_id=task_id,
            objective=objective,
            max_steps=max_steps,
        )
        return task_id

    async def recover_interrupted_sessions(self) -> int:
        """Recover tasks from DB on startup, returns count of recovered tasks."""
        count = 0
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
                    if row.status in (
                        AutoLoopTaskStatus.RUNNING,
                        AutoLoopTaskStatus.RETRYING,
                    ):
                        new_status = AutoLoopTaskStatus.PENDING
                    else:
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
        except Exception as exc:
            logger.error(
                "auto_loop_recovery_failed", error=str(exc), exc_info=True
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
                await runner(record)
            else:
                await self._default_runner(record)

            if record.status == AutoLoopTaskStatus.RUNNING:
                if record.current_step >= record.max_steps - 1:
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
        """Default runner that simulates autonomous task execution."""
        for step in range(record.current_step, record.max_steps):
            if record.status != AutoLoopTaskStatus.RUNNING:
                break
            record.current_step = step
            record.heartbeat_at = time.time()
            await self._persist_status(record, AutoLoopTaskStatus.RUNNING)
            await asyncio.sleep(0.1)
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
        """Detect and handle stalled tasks."""
        now = time.time()
        for record in self._tasks.values():
            if record.status == AutoLoopTaskStatus.RUNNING:
                if record.heartbeat_at is None or (
                    now - record.heartbeat_at > self._heartbeat_timeout
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
                        try:
                            await record.asyncio_task
                        except asyncio.CancelledError:
                            pass
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

                now = datetime.now(timezone.utc)
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
                        existing.finished_at = datetime.utcfromtimestamp(
                            record.finished_at
                        )
                    if record.started_at:
                        existing.started_at = datetime.utcfromtimestamp(
                            record.started_at
                        )
                else:
                    task = AutoLoopTask(
                        id=record.task_id,
                        objective=record.objective,
                        status=status.value,
                        max_steps=record.max_steps,
                        current_step=record.current_step,
                        result=record.result,
                        error=record.error,
                        created_at=datetime.utcfromtimestamp(
                            record.created_at
                        ),
                        started_at=datetime.utcfromtimestamp(record.started_at)
                        if record.started_at
                        else None,
                        finished_at=datetime.utcfromtimestamp(record.finished_at)
                        if record.finished_at
                        else None,
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

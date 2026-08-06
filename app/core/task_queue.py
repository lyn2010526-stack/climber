"""Asynchronous task queue with priority-based scheduling and automatic retries.

Tasks are held in an in-memory sorted list ordered by priority (highest first)
and insertion time (earliest first). All mutations are guarded by an asyncio
lock so the scheduler is safe for concurrent coroutines.
"""

from __future__ import annotations

import asyncio
import threading
import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Lifecycle state of a queued task."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(int, Enum):
    """Scheduling priority, higher values run first."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class QueuedTask(BaseModel):
    """A single task tracked by the scheduler."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.QUEUED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    attempts: int = 0
    max_attempts: int = 3


class TaskScheduler:
    """Priority queue scheduling QUEUED tasks in FIFO order within a priority.

    The ordering list holds only QUEUED task ids sorted by descending priority
    then ascending created_at, so ``poll_next`` always returns the highest
    priority task that has been waiting the longest.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, QueuedTask] = {}
        self._order: list[str] = []
        self._lock: asyncio.Lock = asyncio.Lock()
        self._logger: structlog.BoundLogger = structlog.get_logger(__name__)

    def _resort(self) -> None:
        self._order.sort(key=lambda tid: (-self._tasks[tid].priority.value, self._tasks[tid].created_at))

    async def submit(
        self,
        name: str,
        payload: dict[str, Any] | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_attempts: int = 3,
    ) -> QueuedTask:
        """Enqueue a new task and return it."""
        task = QueuedTask(
            name=name,
            payload=payload or {},
            priority=priority,
            max_attempts=max_attempts,
        )
        async with self._lock:
            self._tasks[task.id] = task
            self._order.append(task.id)
            self._resort()
        self._logger.info("task_submitted", task_id=task.id, name=name, priority=task.priority.value)
        return task

    async def poll_next(self) -> QueuedTask | None:
        """Dequeue the next QUEUED task, mark it RUNNING, and return it."""
        async with self._lock:
            for tid in self._order:
                task = self._tasks.get(tid)
                if task is None or task.status != TaskStatus.QUEUED:
                    continue
                self._order.remove(tid)
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now(UTC)
                self._logger.info("task_started", task_id=task.id, name=task.name)
                return task
            return None

    async def complete(self, task_id: str, result: dict[str, Any]) -> bool:
        """Mark a RUNNING task as SUCCEEDED with the given result."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if task is None or task.status != TaskStatus.RUNNING:
                return False
            task.status = TaskStatus.SUCCEEDED
            task.result = result
            task.completed_at = datetime.now(UTC)
        self._logger.info("task_completed", task_id=task_id, name=task.name)
        return True

    async def fail(self, task_id: str, error: str) -> bool:
        """Mark a RUNNING task failed, re-queuing it for retry when attempts remain."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if task is None or task.status != TaskStatus.RUNNING:
                return False
            task.attempts += 1
            task.error = error
            if task.attempts < task.max_attempts:
                task.status = TaskStatus.QUEUED
                self._order.append(task.id)
                self._resort()
                self._logger.warning(
                    "task_retrying", task_id=task_id, name=task.name, attempts=task.attempts, max_attempts=task.max_attempts
                )
            else:
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now(UTC)
                self._logger.error(
                    "task_failed", task_id=task_id, name=task.name, attempts=task.attempts, error=error
                )
        return True

    async def cancel(self, task_id: str) -> bool:
        """Cancel a QUEUED or RUNNING task."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if task is None or task.status in (TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                return False
            if task.id in self._order:
                self._order.remove(task.id)
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now(UTC)
        self._logger.info("task_cancelled", task_id=task_id, name=task.name)
        return True

    async def status(self, task_id: str) -> QueuedTask | None:
        """Return the task with the given id, or None if it does not exist."""
        async with self._lock:
            return self._tasks.get(task_id)

    async def list(self, status: TaskStatus | None = None, limit: int = 50) -> list[QueuedTask]:
        """List tasks, optionally filtered by status, newest first."""
        async with self._lock:
            tasks = list(self._tasks.values())
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks[:limit]

    async def stats(self) -> dict[str, Any]:
        """Return per-status counts and the average queue wait time in seconds."""
        async with self._lock:
            tasks = list(self._tasks.values())
        counts = {status: sum(1 for t in tasks if t.status == status) for status in TaskStatus}
        now = datetime.now(UTC)
        waits = [((t.started_at or now) - t.created_at).total_seconds() for t in tasks]
        average_wait = sum(waits) / len(waits) if waits else 0.0
        return {
            "by_status": {s.value: c for s, c in counts.items()},
            "total": len(tasks),
            "average_wait_seconds": round(average_wait, 2),
        }


_scheduler: TaskScheduler | None = None
_scheduler_lock = threading.Lock()


async def get_scheduler() -> TaskScheduler:
    """Return the process-wide TaskScheduler singleton."""
    global _scheduler
    if _scheduler is None:
        with _scheduler_lock:
            if _scheduler is None:
                _scheduler = TaskScheduler()
    return _scheduler

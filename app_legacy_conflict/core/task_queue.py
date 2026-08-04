"""Dynamic task queue with priority and concurrency control.

"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Task:
    id: str
    description: str
    priority: float = 0.0
    status: str = "pending"  # pending / in_progress / completed / failed
    result: str | None = None
    dependencies: list[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class TaskQueue:
    """Priority queue for tasks with dynamic re-prioritization and concurrency limit.

    Features:
    - Priority-based ordering
    - Dependency resolution
    - Max concurrent task limit (AGiXT)
    - Dynamic re-prioritization (BabyAGI)
    """

    def __init__(self, max_concurrent: int = 4):
        self._tasks: dict[str, Task] = {}
        self._order: list[str] = []
        self._max_concurrent = max_concurrent
        self._running_count = 0

    def add(self, task: Task) -> None:
        self._tasks[task.id] = task
        self._order.append(task.id)
        self._sort()

    def _sort(self) -> None:
        self._order.sort(key=lambda tid: self._tasks[tid].priority, reverse=True)

    def get_next(self) -> Task | None:
        if self._running_count >= self._max_concurrent:
            return None
        for tid in self._order:
            task = self._tasks[tid]
            if task.status == "pending" and self._dependencies_met(task):
                self._running_count += 1
                task.status = "in_progress"
                return task
        return None

    def _dependencies_met(self, task: Task) -> bool:
        return all(self._tasks.get(dep, None) and self._tasks[dep].status == "completed" for dep in task.dependencies)

    def mark_completed(self, task_id: str, result: str) -> None:
        task = self._tasks.get(task_id)
        if task:
            task.status = "completed"
            task.result = result
            task.completed_at = datetime.now(timezone.utc)
            self._running_count = max(0, self._running_count - 1)
            self._sort()

    def mark_failed(self, task_id: str) -> None:
        task = self._tasks.get(task_id)
        if task:
            task.retry_count += 1
            if task.retry_count >= task.max_retries:
                task.status = "failed"
            else:
                task.status = "pending"
                task.priority += 1.0
            self._running_count = max(0, self._running_count - 1)
            self._sort()

    def reprioritize(self, scoring_fn: Any) -> None:
        for task in self._tasks.values():
            if task.status == "pending":
                task.priority = scoring_fn(task)
        self._sort()

    def list_pending(self) -> list[Task]:
        return [t for t in self._tasks.values() if t.status == "pending"]

    def list_completed(self) -> list[Task]:
        return [t for t in self._tasks.values() if t.status == "completed"]

    def list_running(self) -> list[Task]:
        return [t for t in self._tasks.values() if t.status == "in_progress"]

    def get(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def all(self) -> list[Task]:
        return list(self._tasks.values())

    def set_max_concurrent(self, max_concurrent: int) -> None:
        self._max_concurrent = max(1, max_concurrent)

    @property
    def running_count(self) -> int:
        return self._running_count


task_queue = TaskQueue()

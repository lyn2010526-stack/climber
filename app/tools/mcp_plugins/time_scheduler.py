"""MCP Plugin: Time/Event Scheduler — persistent scheduled tasks.

Supports long-running background tasks, periodic wake-ups,
and cross-session task planning.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskFrequency(str, Enum):
    ONCE = "once"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"


@dataclass
class ScheduledTask:
    id: str
    name: str
    description: str
    scheduled_at: float
    frequency: TaskFrequency
    status: TaskStatus
    last_run: float = 0
    next_run: float = 0
    run_count: int = 0
    max_runs: int = 1
    payload: dict[str, Any] = field(default_factory=dict)


class TimeEventScheduler:
    """Schedule and manage recurring tasks."""

    def __init__(self, storage_path: str = "data/scheduled_tasks.json"):
        self._storage_path = storage_path
        self._tasks: dict[str, ScheduledTask] = {}
        self._load()

    def schedule(
        self,
        name: str,
        description: str,
        delay_seconds: float,
        frequency: TaskFrequency = TaskFrequency.ONCE,
        max_runs: int = 1,
        payload: dict[str, Any] | None = None,
    ) -> ScheduledTask:
        task_id = str(uuid.uuid4())[:8]
        now = time.time()
        task = ScheduledTask(
            id=task_id,
            name=name,
            description=description,
            scheduled_at=now + delay_seconds,
            frequency=frequency,
            status=TaskStatus.PENDING,
            next_run=now + delay_seconds,
            max_runs=max_runs,
            payload=payload or {},
        )
        self._tasks[task_id] = task
        self._save()
        return task

    def get_due_tasks(self) -> list[ScheduledTask]:
        """Get all tasks that are due for execution."""
        now = time.time()
        return [
            t for t in self._tasks.values()
            if t.status == TaskStatus.PENDING and t.next_run <= now
        ]

    def execute_task(self, task_id: str) -> dict[str, Any]:
        """Mark a task as running and update schedule."""
        task = self._tasks.get(task_id)
        if not task:
            return {"error": "Task not found"}

        task.status = TaskStatus.RUNNING
        task.last_run = time.time()
        task.run_count += 1

        # Calculate next run for recurring tasks
        if task.frequency != TaskFrequency.ONCE and task.run_count < task.max_runs:
            intervals = {
                TaskFrequency.HOURLY: 3600,
                TaskFrequency.DAILY: 86400,
                TaskFrequency.WEEKLY: 604800,
            }
            task.next_run = task.last_run + intervals.get(task.frequency, 0)
            task.status = TaskStatus.PENDING
        else:
            task.status = TaskStatus.COMPLETED

        self._save()
        return {
            "task_id": task.id,
            "name": task.name,
            "status": task.status.value,
            "run_count": task.run_count,
        }

    def cancel_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False
        task.status = TaskStatus.CANCELLED
        self._save()
        return True

    def list_tasks(
        self,
        status: TaskStatus | None = None,
    ) -> list[dict[str, Any]]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return [
            {
                "id": t.id,
                "name": t.name,
                "status": t.status.value,
                "frequency": t.frequency.value,
                "next_run": t.next_run,
                "run_count": t.run_count,
                "max_runs": t.max_runs,
            }
            for t in tasks
        ]

    def get_task(self, task_id: str) -> ScheduledTask | None:
        return self._tasks.get(task_id)

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "schedule_task",
                "description": "Schedule a task for future execution",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "delay_seconds": {"type": "number"},
                        "frequency": {
                            "type": "string",
                            "enum": ["once", "hourly", "daily", "weekly"],
                        },
                        "max_runs": {"type": "integer"},
                    },
                    "required": ["name", "description", "delay_seconds"],
                },
            },
            {
                "name": "get_due_tasks",
                "description": "Get all tasks that are due for execution",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "cancel_task",
                "description": "Cancel a scheduled task",
                "parameters": {
                    "type": "object",
                    "properties": {"task_id": {"type": "string"}},
                    "required": ["task_id"],
                },
            },
        ]

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._storage_path), exist_ok=True)
        data = {
            tid: {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "scheduled_at": t.scheduled_at,
                "frequency": t.frequency.value,
                "status": t.status.value,
                "last_run": t.last_run,
                "next_run": t.next_run,
                "run_count": t.run_count,
                "max_runs": t.max_runs,
                "payload": t.payload,
            }
            for tid, t in self._tasks.items()
        }
        with open(self._storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self) -> None:
        if not os.path.exists(self._storage_path):
            return
        try:
            with open(self._storage_path) as f:
                data = json.load(f)
            for tid, t in data.items():
                self._tasks[tid] = ScheduledTask(
                    id=t["id"],
                    name=t["name"],
                    description=t["description"],
                    scheduled_at=t.get("scheduled_at", 0),
                    frequency=TaskFrequency(t.get("frequency", "once")),
                    status=TaskStatus(t.get("status", "pending")),
                    last_run=t.get("last_run", 0),
                    next_run=t.get("next_run", 0),
                    run_count=t.get("run_count", 0),
                    max_runs=t.get("max_runs", 1),
                    payload=t.get("payload", {}),
                )
        except (json.JSONDecodeError, KeyError):
            pass

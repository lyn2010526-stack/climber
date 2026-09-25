"""Scheduled Task Scheduler — periodic unattended project inspection and automation.

Supports:
- Cron-like scheduling
- Recurring task execution
- Task inspection logging
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from croniter import croniter


@dataclass
class ScheduledTask:
    id: str
    name: str
    description: str
    cron_expression: str        # Simple: "*/5 * * * *" = every 5 min
    task_type: str              # "inspect", "audit", "backup", "custom"
    enabled: bool = True
    last_run: float | None = None
    next_run: float | None = None
    run_count: int = 0
    max_runs: int | None = None  # None = unlimited
    config: dict[str, Any] = field(default_factory=dict)


class TaskScheduler:
    """Manages scheduled tasks for periodic execution."""

    def __init__(self):
        self._tasks: dict[str, ScheduledTask] = {}
        self._handlers: dict[str, Callable] = {}
        self._running = False

    def register_handler(self, task_type: str, handler: Callable):
        """Register a handler for a task type."""
        self._handlers[task_type] = handler

    def add_task(self, task: ScheduledTask):
        """Add a scheduled task."""
        self._tasks[task.id] = task
        task.next_run = self._calc_next_run(task.cron_expression)

    def remove_task(self, task_id: str):
        """Remove a scheduled task."""
        self._tasks.pop(task_id, None)

    def toggle_task(self, task_id: str):
        """Toggle task enabled/disabled."""
        task = self._tasks.get(task_id)
        if task:
            task.enabled = not task.enabled

    def list_tasks(self) -> list[ScheduledTask]:
        """List all scheduled tasks."""
        return list(self._tasks.values())

    def get_due_tasks(self) -> list[ScheduledTask]:
        """Get tasks that are due for execution."""
        now = time.time()
        return [
            t for t in self._tasks.values()
            if t.enabled and t.next_run and t.next_run <= now
        ]

    async def run_pending(self):
        """Run all due tasks."""
        due = self.get_due_tasks()
        for task in due:
            handler = self._handlers.get(task.task_type)
            if handler:
                try:
                    await handler(task)
                    task.run_count += 1
                    task.last_run = time.time()

                    # Check max runs
                    if task.max_runs and task.run_count >= task.max_runs:
                        task.enabled = False
                except Exception as e:
                    task.config["last_error"] = str(e)

            task.next_run = self._calc_next_run(task.cron_expression)

    def _calc_next_run(self, cron: str) -> float:
        """Calculate the next run time for a standard five-field cron expression."""
        now = time.time()
        try:
            return float(croniter(cron, now).get_next())
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid cron expression: {cron}") from exc


# ─── Built-in Scheduled Task Definitions ────────────────────────────────────

SCHEDULED_TASK_TEMPLATES = [
    {
        "name": "Daily Security Scan",
        "description": "Scan project for security vulnerabilities",
        "cron": "0 2 * * *",  # 2 AM daily
        "type": "audit",
    },
    {
        "name": "Dependency Update Check",
        "description": "Check for outdated dependencies",
        "cron": "0 10 * * 1",  # Monday 10 AM
        "type": "inspect",
    },
    {
        "name": "Memory Cleanup",
        "description": "Clean up expired memory entries",
        "cron": "*/30 * * * *",  # Every 30 min
        "type": "custom",
    },
]


# Singleton
task_scheduler = TaskScheduler()

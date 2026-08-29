"""Layer 2 — medium-term (task-level) memory.

Holds the current task's operation history, intermediate results, and
screenshots while the task is running. On task completion it is either
promoted into long-term memory or archived.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class TaskRecord:
    operation: str
    result: Any = None
    screenshot: str = ""
    ts: float = field(default_factory=time.time)
    seq: int = 0


@dataclass
class TaskMemory:
    """Per-task operation history with promotion/archival support."""

    task_id: str = ""
    title: str = ""
    records: list[TaskRecord] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    _seq: int = 0

    def add(
        self,
        operation: str,
        result: Any = None,
        screenshot: str = "",
    ) -> TaskRecord:
        self._seq += 1
        record = TaskRecord(
            operation=operation,
            result=result,
            screenshot=screenshot,
            seq=self._seq,
        )
        self.records.append(record)
        return record

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "started_at": self.started_at,
            "records": [
                {
                    "seq": r.seq,
                    "operation": r.operation,
                    "result": r.result,
                    "screenshot": r.screenshot,
                    "ts": r.ts,
                }
                for r in self.records
            ],
        }

    @property
    def operation_count(self) -> int:
        return len(self.records)


class MediumTermMemory:
    """Manages the active task memory and its promotion lifecycle."""

    def __init__(self, max_records: int = 500) -> None:
        self._active: TaskMemory | None = None
        self._archived: dict[str, TaskMemory] = {}
        self._max_records = max_records

    def begin_task(self, title: str = "") -> str:
        task_id = str(uuid.uuid4())
        self._active = TaskMemory(task_id=task_id, title=title)
        return task_id

    def add_record(
        self,
        operation: str,
        result: Any = None,
        screenshot: str = "",
    ) -> TaskRecord | None:
        if self._active is None:
            return None
        record = self._active.add(operation, result, screenshot)
        if len(self._active.records) > self._max_records:
            self._active.records = self._active.records[-self._max_records:]
        return record

    def get_active(self) -> TaskMemory | None:
        return self._active

    def get(self, task_id: str) -> TaskMemory | None:
        if self._active and self._active.task_id == task_id:
            return self._active
        return self._archived.get(task_id)

    async def finish_task(
        self,
        archive: bool = True,
        promote_fn: Any = None,
    ) -> TaskMemory | None:
        """Complete the active task, archiving or promoting it.

        Args:
            archive: keep the task in the archived store.
            promote_fn: optional async ``promote(task_memory) -> None`` hook
                that persists distilled facts to long-term memory.
        """
        if self._active is None:
            return None
        task = self._active
        if promote_fn is not None:
            try:
                await promote_fn(task)
            except Exception as exc:
                logger.warning("memory.medium_term.promote_failed", error=str(exc))
        if archive:
            self._archived[task.task_id] = task
        self._active = None
        return task

    def get_task_history(self, task_id: str) -> list[dict[str, Any]]:
        task = self.get(task_id)
        if task is None:
            return []
        return [
            {
                "seq": r.seq,
                "operation": r.operation,
                "result": r.result,
                "screenshot": r.screenshot,
                "ts": r.ts,
            }
            for r in task.records
        ]

    def archived_ids(self) -> list[str]:
        return list(self._archived.keys())

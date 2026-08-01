"""Event-driven task execution event bus.

Publishes and stores task lifecycle events with SQLite-backed audit trail.
Extends the core EventBus pattern with task-specific event types and persistence.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

import structlog

logger = structlog.get_logger()

TaskEventHandler = Callable[["TaskEvent"], Coroutine[Any, Any, None] | None]


@dataclass
class TaskEvent:
    """Event emitted during task execution."""

    event_type: str
    task_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "data": self.data,
        }


class EventBus:
    """Task event bus with SQLite-backed audit trail.

    Publishes events for task state transitions, tool calls,
    sub-task completions, and HITL requests.
    """

    EVENT_CREATED = "created"
    EVENT_STARTED = "started"
    EVENT_COMPLETED = "completed"
    EVENT_FAILED = "failed"
    EVENT_PAUSED = "paused"
    EVENT_RESUMED = "resumed"
    EVENT_NEEDS_APPROVAL = "needs_approval"
    EVENT_SUBTASK_COMPLETED = "subtask_completed"
    EVENT_TOOL_CALL = "tool_call"

    def __init__(self, db_path: str = ":memory:"):
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._subscribers: dict[str, list[TaskEventHandler]] = defaultdict(list)
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS task_events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                task_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                data_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_task_events_task_id
                ON task_events(task_id);
            CREATE INDEX IF NOT EXISTS idx_task_events_type
                ON task_events(event_type);
        """)
        self._conn.commit()

    def subscribe(self, event_type: str, handler: TaskEventHandler) -> None:
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: TaskEventHandler) -> bool:
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)
            return True
        return False

    async def publish(self, event: TaskEvent) -> None:
        self._persist_event(event)
        handlers = list(self._subscribers.get(event.event_type, []))
        for handler in handlers:
            try:
                result = handler(event)
                if hasattr(result, "__await__"):
                    await result
            except Exception as e:
                logger.warning("event_bus.handler_execution_failed", error=str(e))

    def _persist_event(self, event: TaskEvent) -> None:
        self._conn.execute(
            """
            INSERT INTO task_events (event_id, event_type, task_id, timestamp, data_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.event_type,
                event.task_id,
                event.timestamp,
                json.dumps(event.data),
            ),
        )
        self._conn.commit()

    def get_history(
        self,
        task_id: str | None = None,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[TaskEvent]:
        query = "SELECT * FROM task_events WHERE 1=1"
        params: list[Any] = []
        if task_id:
            query += " AND task_id = ?"
            params.append(task_id)
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        rows = self._conn.execute(query, params).fetchall()
        events = []
        for row in rows:
            events.append(
                TaskEvent(
                    event_id=row["event_id"],
                    event_type=row["event_type"],
                    task_id=row["task_id"],
                    timestamp=row["timestamp"],
                    data=json.loads(row["data_json"]),
                )
            )
        return events

    def clear_history(self) -> None:
        self._conn.execute("DELETE FROM task_events")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

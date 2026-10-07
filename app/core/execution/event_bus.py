"""Event-driven task execution event bus.

Publishes and stores task lifecycle events with SQLite-backed audit trail.
Extends the core EventBus pattern with task-specific event types and persistence.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from collections import defaultdict
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import structlog

logger = structlog.get_logger()

TaskEventHandler = Callable[["TaskEvent"], Coroutine[Any, Any, None] | None]


@dataclass
class TaskEvent:
    """Event emitted during task execution."""

    event_type: str
    task_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    data: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sequence: int | None = None
    schema_version: int = 1
    correlation_id: str | None = None
    causation_id: str | None = None
    producer: str = "event_bus"

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "data": self.data,
            "sequence": self.sequence,
            "schema_version": self.schema_version,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "producer": self.producer,
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
    EVENT_CANCELLED = "cancelled"
    EVENT_PAUSED = "paused"
    EVENT_RESUMED = "resumed"
    EVENT_NEEDS_APPROVAL = "needs_approval"
    EVENT_SUBTASK_COMPLETED = "subtask_completed"
    EVENT_TOOL_CALL = "tool_call"

    def __init__(self, db_path: str | None = None):
        """Create the bus, persisting events to ``db_path`` when provided.

        ``db_path=None`` keeps events in an in-memory SQLite database. A file
        path makes the audit trail survive process restarts, which is what the
        task-recovery flow relies on after a crash.
        """
        self._db_path = db_path if db_path is not None else ":memory:"
        if self._db_path != ":memory:":
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        # The sqlite3 connection is shared by async publishers; a lock keeps
        # concurrent writes from interleaving inside a transaction.
        self._lock = threading.Lock()
        self._subscribers: dict[str, list[TaskEventHandler]] = defaultdict(list)
        self._closed = False
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS task_events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                task_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                data_json TEXT NOT NULL DEFAULT '{}',
                sequence INTEGER,
                schema_version INTEGER NOT NULL DEFAULT 1,
                correlation_id TEXT,
                causation_id TEXT,
                producer TEXT NOT NULL DEFAULT 'event_bus'
            );
            CREATE TABLE IF NOT EXISTS task_event_sequence (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                value INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_task_events_task_id
                ON task_events(task_id);
            CREATE INDEX IF NOT EXISTS idx_task_events_type
                ON task_events(event_type);
        """)
        columns = {
            row[1] for row in self._conn.execute("PRAGMA table_info(task_events)").fetchall()
        }
        for name, definition in {
            "sequence": "INTEGER",
            "schema_version": "INTEGER NOT NULL DEFAULT 1",
            "correlation_id": "TEXT",
            "causation_id": "TEXT",
            "producer": "TEXT NOT NULL DEFAULT 'event_bus'",
        }.items():
            if name not in columns:
                self._conn.execute(f"ALTER TABLE task_events ADD COLUMN {name} {definition}")
        self._conn.execute(
            "INSERT OR IGNORE INTO task_event_sequence (id, value) "
            "SELECT 1, COALESCE(MAX(sequence), 0) FROM task_events"
        )
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
                    await cast("Coroutine[Any, Any, None]", result)
            except Exception as e:
                logger.warning("event_bus.handler_execution_failed", error=str(e))

    def _persist_event(self, event: TaskEvent) -> None:
        with self._lock:
            if event.sequence is None:
                self._conn.execute("UPDATE task_event_sequence SET value = value + 1 WHERE id = 1")
                event.sequence = self._conn.execute(
                    "SELECT value FROM task_event_sequence WHERE id = 1"
                ).fetchone()[0]
            self._conn.execute(
                """
                INSERT INTO task_events (
                    event_id, event_type, task_id, timestamp, data_json, sequence,
                    schema_version, correlation_id, causation_id, producer
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.event_type,
                    event.task_id,
                    event.timestamp,
                    json.dumps(event.data),
                    event.sequence,
                    event.schema_version,
                    event.correlation_id,
                    event.causation_id,
                    event.producer,
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
        query += " ORDER BY sequence DESC, timestamp DESC LIMIT ?"
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
                    sequence=row["sequence"],
                    schema_version=row["schema_version"] or 1,
                    correlation_id=row["correlation_id"],
                    causation_id=row["causation_id"],
                    producer=row["producer"] or "event_bus",
                )
            )
        return events

    def replay(
        self,
        task_id: str | None = None,
        *,
        after_sequence: int | None = None,
        event_type: str | None = None,
        limit: int | None = None,
    ) -> list[TaskEvent]:
        """Replay persisted events in causal append order.

        ``get_history`` remains newest-first for existing callers. Replay is
        the event-sourced path: consumers fold this ordered stream into a
        projection instead of reading mutable task state as authoritative.
        """
        query = "SELECT * FROM task_events WHERE 1=1"
        params: list[Any] = []
        if task_id:
            query += " AND task_id = ?"
            params.append(task_id)
        if after_sequence is not None:
            query += " AND sequence > ?"
            params.append(after_sequence)
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        query += " ORDER BY sequence ASC, timestamp ASC, event_id ASC"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        rows = self._conn.execute(query, params).fetchall()
        return [self._event_from_row(row) for row in rows]

    @staticmethod
    def _event_from_row(row: sqlite3.Row) -> TaskEvent:
        return TaskEvent(
            event_id=row["event_id"],
            event_type=row["event_type"],
            task_id=row["task_id"],
            timestamp=row["timestamp"],
            data=json.loads(row["data_json"]),
            sequence=row["sequence"],
            schema_version=row["schema_version"] or 1,
            correlation_id=row["correlation_id"],
            causation_id=row["causation_id"],
            producer=row["producer"] or "event_bus",
        )

    def clear_history(self) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM task_events")
            self._conn.commit()

    def get_pending_task_ids(self) -> list[str]:
        """Task ids that were started but never reached a terminal state.

        Recovery hook: after a crash, tasks that published ``created`` or
        ``started`` but never ``completed``/``failed``/``cancelled`` are the
        ones that need resumption or manual review.
        """
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT DISTINCT task_id FROM task_events
                WHERE event_type IN (?, ?)
                AND task_id NOT IN (
                    SELECT task_id FROM task_events
                    WHERE event_type IN (?, ?, ?)
                )
                ORDER BY timestamp
                """,
                (
                    self.EVENT_CREATED,
                    self.EVENT_STARTED,
                    self.EVENT_COMPLETED,
                    self.EVENT_FAILED,
                    self.EVENT_CANCELLED,
                ),
            ).fetchall()
        return [row["task_id"] for row in rows]

    def close(self) -> None:
        if self._closed:
            return
        with self._lock:
            self._conn.close()
            self._closed = True


_default_event_bus_path = Path("data") / "task_events.db"

_event_bus: EventBus | None = None


def get_task_event_bus(db_path: str | None = None) -> EventBus:
    """Return the process-wide persistent event bus.

    Uses a file-backed SQLite database so the audit trail survives restarts,
    enabling task recovery after a crash. Pass ``db_path=":memory:"`` for a
    throwaway instance (tests).
    """
    global _event_bus, _default_event_bus_path
    if _event_bus is None:
        _event_bus = EventBus(
            db_path=db_path if db_path is not None else str(_default_event_bus_path)
        )
    return _event_bus


def reset_task_event_bus() -> None:
    """Drop the process-wide singleton (used by tests)."""
    global _event_bus
    _event_bus = None

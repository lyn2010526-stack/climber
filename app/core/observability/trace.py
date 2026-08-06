"""Enhanced trace system for observability.

Provides hierarchical span tracking with parent-child relationships,
configurable sampling, and SQLite-backed persistence via TraceModel.
"""

from __future__ import annotations

import random
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class TraceSpan:
    """A single trace span representing a unit of work within a trace.

    Spans form a tree structure via parent_span_id, enabling
    reconstruction of full call hierarchies.
    """

    span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_span_id: str = ""
    operation: str = ""
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    ended_at: str = ""
    status: str = "ok"
    tags: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation": self.operation,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "status": self.status,
            "tags": self.tags,
            "events": self.events,
        }


class TraceCollector:
    """Collects and persists trace spans with sampling support.

    Spans are stored in SQLite and can be retrieved by trace_id
    to reconstruct the full trace tree.
    """

    def __init__(self, db_path: str = ":memory:", sample_rate: float = 1.0):
        self._db_path = db_path
        self._sample_rate = sample_rate
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS trace_spans (
                span_id TEXT PRIMARY KEY,
                trace_id TEXT NOT NULL,
                parent_span_id TEXT DEFAULT '',
                operation TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'ok',
                tags_json TEXT NOT NULL DEFAULT '{}',
                events_json TEXT NOT NULL DEFAULT '[]'
            );
            CREATE INDEX IF NOT EXISTS idx_trace_spans_trace_id
                ON trace_spans(trace_id);
            CREATE INDEX IF NOT EXISTS idx_trace_spans_parent
                ON trace_spans(parent_span_id);
        """)
        self._conn.commit()

    def _should_sample(self) -> bool:
        if self._sample_rate >= 1.0:
            return True
        return random.random() < self._sample_rate

    def start_span(
        self,
        operation: str,
        trace_id: str = "",
        parent_span_id: str = "",
        tags: dict[str, Any] | None = None,
    ) -> TraceSpan | None:
        """Start a new span. Returns None if sampled out."""
        if not self._should_sample():
            return None

        span = TraceSpan(
            trace_id=trace_id or str(uuid.uuid4()),
            parent_span_id=parent_span_id,
            operation=operation,
            tags=tags or {},
        )
        self._persist_span(span)
        return span

    def end_span(self, span: TraceSpan, status: str = "ok") -> None:
        """End a span and persist the final state."""
        span.ended_at = datetime.now(UTC).isoformat()
        span.status = status
        self._persist_span(span)

    def add_event(self, span: TraceSpan, event_type: str, data: dict[str, Any] | None = None) -> None:
        """Add an event to an existing span."""
        event = {
            "type": event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": data or {},
        }
        span.events.append(event)
        self._persist_span(span)

    def get_trace(self, trace_id: str) -> list[TraceSpan]:
        """Retrieve all spans for a given trace, ordered by start time."""
        rows = self._conn.execute(
            "SELECT * FROM trace_spans WHERE trace_id = ? ORDER BY started_at",
            (trace_id,),
        ).fetchall()
        return [self._row_to_span(row) for row in rows]

    def get_span(self, span_id: str) -> TraceSpan | None:
        """Retrieve a single span by ID."""
        row = self._conn.execute(
            "SELECT * FROM trace_spans WHERE span_id = ?", (span_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_span(row)

    def list_traces(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        """List distinct trace IDs with their root operation and span count."""
        rows = self._conn.execute(
            """
            SELECT trace_id, MIN(started_at) as started_at,
                   COUNT(*) as span_count,
                   SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count
            FROM trace_spans
            GROUP BY trace_id
            ORDER BY started_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        return [
            {
                "trace_id": row["trace_id"],
                "started_at": row["started_at"],
                "span_count": row["span_count"],
                "error_count": row["error_count"],
            }
            for row in rows
        ]

    def get_children(self, parent_span_id: str) -> list[TraceSpan]:
        """Get all child spans of a given parent."""
        rows = self._conn.execute(
            "SELECT * FROM trace_spans WHERE parent_span_id = ? ORDER BY started_at",
            (parent_span_id,),
        ).fetchall()
        return [self._row_to_span(row) for row in rows]

    def _persist_span(self, span: TraceSpan) -> None:
        import json

        self._conn.execute(
            """
            INSERT OR REPLACE INTO trace_spans
            (span_id, trace_id, parent_span_id, operation, started_at,
             ended_at, status, tags_json, events_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                span.span_id,
                span.trace_id,
                span.parent_span_id,
                span.operation,
                span.started_at,
                span.ended_at,
                span.status,
                json.dumps(span.tags),
                json.dumps(span.events),
            ),
        )
        self._conn.commit()

    def _row_to_span(self, row: sqlite3.Row) -> TraceSpan:
        import json

        return TraceSpan(
            trace_id=row["trace_id"],
            span_id=row["span_id"],
            parent_span_id=row["parent_span_id"],
            operation=row["operation"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            status=row["status"],
            tags=json.loads(row["tags_json"]),
            events=json.loads(row["events_json"]),
        )

    def close(self) -> None:
        self._conn.close()

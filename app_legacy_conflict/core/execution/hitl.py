"""Human-in-the-Loop (HITL) approval manager.

Manages approval requests for sensitive operations during task execution.
Tasks requiring HITL approval are paused until approved, rejected, or expired.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any


HITLStatusPending = "pending"
HITLStatusApproved = "approved"
HITLStatusRejected = "rejected"
HITLStatusExpired = "expired"


@dataclass
class HITLRequest:
    """A request for human approval."""

    id: str
    task_id: str
    action_type: str
    payload: dict[str, Any]
    requested_at: str
    expires_at: str
    status: str = HITLStatusPending
    resolved_at: str = ""
    resolved_by: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "action_type": self.action_type,
            "payload": self.payload,
            "requested_at": self.requested_at,
            "expires_at": self.expires_at,
            "status": self.status,
            "resolved_at": self.resolved_at,
            "resolved_by": self.resolved_by,
        }


class HITLManager:
    """Manages HITL approval requests with SQLite persistence."""

    def __init__(
        self,
        db_path: str = ":memory:",
        default_ttl_seconds: int = 3600,
        auto_approve_actions: set[str] | None = None,
    ):
        self._db_path = db_path
        self._default_ttl = default_ttl_seconds
        self._auto_approve_actions = auto_approve_actions or set()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS hitl_requests (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                requested_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                resolved_at TEXT DEFAULT '',
                resolved_by TEXT DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_hitl_task_id ON hitl_requests(task_id);
            CREATE INDEX IF NOT EXISTS idx_hitl_status ON hitl_requests(status);
        """)
        self._conn.commit()

    def create_request(
        self,
        task_id: str,
        action_type: str,
        payload: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
    ) -> HITLRequest:
        now = datetime.now(timezone.utc)
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        request = HITLRequest(
            id=str(uuid.uuid4()),
            task_id=task_id,
            action_type=action_type,
            payload=payload or {},
            requested_at=now.isoformat(),
            expires_at=(now + timedelta(seconds=ttl)).isoformat(),
        )
        if action_type in self._auto_approve_actions:
            request.status = HITLStatusApproved
            request.resolved_at = now.isoformat()
            request.resolved_by = "auto"
        self._persist_request(request)
        return request

    def approve(self, request_id: str, resolved_by: str = "human") -> HITLRequest | None:
        request = self.get_request(request_id)
        if not request or request.status != HITLStatusPending:
            return None
        request.status = HITLStatusApproved
        request.resolved_at = datetime.now(timezone.utc).isoformat()
        request.resolved_by = resolved_by
        self._persist_request(request)
        return request

    def reject(self, request_id: str, resolved_by: str = "human") -> HITLRequest | None:
        request = self.get_request(request_id)
        if not request or request.status != HITLStatusPending:
            return None
        request.status = HITLStatusRejected
        request.resolved_at = datetime.now(timezone.utc).isoformat()
        request.resolved_by = resolved_by
        self._persist_request(request)
        return request

    def expire(self, request_id: str) -> HITLRequest | None:
        request = self.get_request(request_id)
        if not request or request.status != HITLStatusPending:
            return None
        request.status = HITLStatusExpired
        request.resolved_at = datetime.now(timezone.utc).isoformat()
        request.resolved_by = "system"
        self._persist_request(request)
        return request

    def get_pending(self, task_id: str | None = None) -> list[HITLRequest]:
        now = datetime.now(timezone.utc).isoformat()
        if task_id:
            rows = self._conn.execute(
                "SELECT * FROM hitl_requests WHERE task_id = ? AND status = ? AND expires_at > ?",
                (task_id, HITLStatusPending, now),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM hitl_requests WHERE status = ? AND expires_at > ?",
                (HITLStatusPending, now),
            ).fetchall()
        return [self._row_to_request(row) for row in rows]

    def get_expired(self) -> list[HITLRequest]:
        now = datetime.now(timezone.utc).isoformat()
        rows = self._conn.execute(
            "SELECT * FROM hitl_requests WHERE status = ? AND expires_at <= ?",
            (HITLStatusPending, now),
        ).fetchall()
        return [self._row_to_request(row) for row in rows]

    def expire_pending(self) -> list[HITLRequest]:
        expired = self.get_expired()
        for req in expired:
            self.expire(req.id)
        return expired

    def get_request(self, request_id: str) -> HITLRequest | None:
        row = self._conn.execute(
            "SELECT * FROM hitl_requests WHERE id = ?", (request_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_request(row)

    def get_requests_for_task(self, task_id: str) -> list[HITLRequest]:
        rows = self._conn.execute(
            "SELECT * FROM hitl_requests WHERE task_id = ?", (task_id,)
        ).fetchall()
        return [self._row_to_request(row) for row in rows]

    def _persist_request(self, request: HITLRequest) -> None:
        import json

        self._conn.execute(
            """
            INSERT OR REPLACE INTO hitl_requests
            (id, task_id, action_type, payload_json, requested_at, expires_at,
             status, resolved_at, resolved_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request.id,
                request.task_id,
                request.action_type,
                json.dumps(request.payload),
                request.requested_at,
                request.expires_at,
                request.status,
                request.resolved_at,
                request.resolved_by,
            ),
        )
        self._conn.commit()

    def _row_to_request(self, row: sqlite3.Row) -> HITLRequest:
        import json

        return HITLRequest(
            id=row["id"],
            task_id=row["task_id"],
            action_type=row["action_type"],
            payload=json.loads(row["payload_json"]),
            requested_at=row["requested_at"],
            expires_at=row["expires_at"],
            status=row["status"],
            resolved_at=row["resolved_at"],
            resolved_by=row["resolved_by"],
        )

    def close(self) -> None:
        self._conn.close()

"""Global emergency stop manager.

Provides a system-wide kill switch that blocks all new task executions
and signals running tasks to cancel. Supports manual activation and
automatic triggers based on error rates or security violations.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class EmergencyStopRecord:
    """Record of an emergency stop activation or deactivation."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action: str = ""
    triggered_by: str = ""
    reason: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    auto_trigger: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "triggered_by": self.triggered_by,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "auto_trigger": self.auto_trigger,
        }


class EmergencyStopManager:
    """Manages the global emergency stop state.

    When activated:
    - All new task executions are blocked
    - Running tasks receive a cancellation signal
    - An audit log entry is created for each state change

    Supports automatic triggers based on configurable thresholds
    (e.g., excessive error rate, security violation).
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        error_rate_threshold: float = 0.5,
        error_window_seconds: int = 300,
    ):
        self._db_path = db_path
        self._error_rate_threshold = error_rate_threshold
        self._error_window_seconds = error_window_seconds
        self._activated = False
        self._activation_reason = ""
        self._activated_by = ""
        self._activated_at = ""
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()
        self._load_state()

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS emergency_stop_state (
                id TEXT PRIMARY KEY,
                is_activated INTEGER NOT NULL DEFAULT 0,
                reason TEXT DEFAULT '',
                activated_by TEXT DEFAULT '',
                activated_at TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS emergency_stop_log (
                id TEXT PRIMARY KEY,
                action TEXT NOT NULL,
                triggered_by TEXT DEFAULT '',
                reason TEXT DEFAULT '',
                timestamp TEXT NOT NULL,
                auto_trigger INTEGER NOT NULL DEFAULT 0
            );
        """)
        self._conn.commit()

    def _load_state(self) -> None:
        row = self._conn.execute(
            "SELECT * FROM emergency_stop_state WHERE id = 'global'"
        ).fetchone()
        if row:
            self._activated = bool(row["is_activated"])
            self._activation_reason = row["reason"]
            self._activated_by = row["activated_by"]
            self._activated_at = row["activated_at"]

    def activate(
        self,
        reason: str = "manual activation",
        triggered_by: str = "user",
        auto_trigger: bool = False,
    ) -> EmergencyStopRecord:
        """Activate the emergency stop.

        Blocks all new task executions and signals running tasks.
        """
        self._activated = True
        self._activation_reason = reason
        self._activated_by = triggered_by
        self._activated_at = datetime.now(UTC).isoformat()
        self._persist_state()
        record = EmergencyStopRecord(
            action="activate",
            triggered_by=triggered_by,
            reason=reason,
            auto_trigger=auto_trigger,
        )
        self._persist_log(record)
        return record

    def deactivate(
        self,
        reason: str = "manual deactivation",
        triggered_by: str = "user",
    ) -> EmergencyStopRecord:
        """Deactivate the emergency stop, allowing tasks to proceed."""
        self._activated = False
        self._activation_reason = ""
        self._activated_by = ""
        self._activated_at = ""
        self._persist_state()
        record = EmergencyStopRecord(
            action="deactivate",
            triggered_by=triggered_by,
            reason=reason,
        )
        self._persist_log(record)
        return record

    def is_activated(self) -> bool:
        """Check if the emergency stop is currently active."""
        return self._activated

    def get_status(self) -> dict[str, Any]:
        """Get the current emergency stop status."""
        return {
            "is_activated": self._activated,
            "reason": self._activation_reason,
            "activated_by": self._activated_by,
            "activated_at": self._activated_at,
        }

    def get_log(self, limit: int = 50) -> list[EmergencyStopRecord]:
        """Retrieve the emergency stop activation/deactivation log."""
        rows = self._conn.execute(
            "SELECT * FROM emergency_stop_log ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def check_auto_trigger(
        self,
        recent_error_count: int,
        recent_total_count: int,
    ) -> EmergencyStopRecord | None:
        """Check if automatic emergency stop should be triggered.

        Activates the stop if the error rate exceeds the threshold.
        """
        if recent_total_count == 0:
            return None
        error_rate = recent_error_count / recent_total_count
        if error_rate >= self._error_rate_threshold:
            return self.activate(
                reason=f"auto-triggered: error rate {error_rate:.0%} exceeds threshold {self._error_rate_threshold:.0%}",
                triggered_by="system",
                auto_trigger=True,
            )
        return None

    def _persist_state(self) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO emergency_stop_state
            (id, is_activated, reason, activated_by, activated_at)
            VALUES ('global', ?, ?, ?, ?)
            """,
            (
                1 if self._activated else 0,
                self._activation_reason,
                self._activated_by,
                self._activated_at,
            ),
        )
        self._conn.commit()

    def _persist_log(self, record: EmergencyStopRecord) -> None:
        self._conn.execute(
            """
            INSERT INTO emergency_stop_log
            (id, action, triggered_by, reason, timestamp, auto_trigger)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                record.action,
                record.triggered_by,
                record.reason,
                record.timestamp,
                1 if record.auto_trigger else 0,
            ),
        )
        self._conn.commit()

    def _row_to_record(self, row: sqlite3.Row) -> EmergencyStopRecord:
        return EmergencyStopRecord(
            id=row["id"],
            action=row["action"],
            triggered_by=row["triggered_by"],
            reason=row["reason"],
            timestamp=row["timestamp"],
            auto_trigger=bool(row["auto_trigger"]),
        )

    def close(self) -> None:
        self._conn.close()

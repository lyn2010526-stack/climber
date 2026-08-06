"""Decision audit chain for compliance and traceability.

Logs every routing decision, tool selection, and model switch
in an append-only, immutable audit trail.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class AuditEntry:
    """Immutable record of a single decision made by the agent system.

    Entries are append-only: once created, they are never modified
    or deleted, ensuring a complete audit trail for compliance.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    agent_id: str = ""
    session_id: str = ""
    decision_type: str = ""
    input_summary: str = ""
    output_summary: str = ""
    rationale: str = ""
    confidence: float = 0.0
    alternatives_considered: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "decision_type": self.decision_type,
            "input_summary": self.input_summary,
            "output_summary": self.output_summary,
            "rationale": self.rationale,
            "confidence": self.confidence,
            "alternatives_considered": self.alternatives_considered,
        }


class AuditChain:
    """Append-only audit chain for decision tracking.

    Every routing decision, tool selection, and model switch
    is logged as an immutable entry.
    """

    def __init__(self, db_path: str = ":memory:"):
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS audit_entries (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                agent_id TEXT DEFAULT '',
                session_id TEXT DEFAULT '',
                decision_type TEXT NOT NULL,
                input_summary TEXT DEFAULT '',
                output_summary TEXT DEFAULT '',
                rationale TEXT DEFAULT '',
                confidence REAL DEFAULT 0.0,
                alternatives_json TEXT NOT NULL DEFAULT '[]'
            );
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp
                ON audit_entries(timestamp);
            CREATE INDEX IF NOT EXISTS idx_audit_decision_type
                ON audit_entries(decision_type);
            CREATE INDEX IF NOT EXISTS idx_audit_session
                ON audit_entries(session_id);
        """)
        self._conn.commit()

    def log_decision(
        self,
        decision_type: str,
        input_summary: str = "",
        output_summary: str = "",
        rationale: str = "",
        confidence: float = 0.0,
        alternatives_considered: list[str] | None = None,
        agent_id: str = "",
        session_id: str = "",
    ) -> AuditEntry:
        """Log a decision. Entries are immutable once created."""
        entry = AuditEntry(
            decision_type=decision_type,
            input_summary=input_summary,
            output_summary=output_summary,
            rationale=rationale,
            confidence=confidence,
            alternatives_considered=alternatives_considered or [],
            agent_id=agent_id,
            session_id=session_id,
        )
        self._persist_entry(entry)
        return entry

    def get_chain(
        self,
        limit: int = 100,
        offset: int = 0,
        session_id: str | None = None,
    ) -> list[AuditEntry]:
        """Retrieve audit entries, optionally filtered by session."""
        if session_id:
            rows = self._conn.execute(
                "SELECT * FROM audit_entries WHERE session_id = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                (session_id, limit, offset),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM audit_entries ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def get_entry(self, entry_id: str) -> AuditEntry | None:
        """Retrieve a single audit entry by ID."""
        row = self._conn.execute(
            "SELECT * FROM audit_entries WHERE id = ?", (entry_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_entry(row)

    def search_by_type(self, decision_type: str, limit: int = 50) -> list[AuditEntry]:
        """Search audit entries by decision type."""
        rows = self._conn.execute(
            "SELECT * FROM audit_entries WHERE decision_type = ? ORDER BY timestamp DESC LIMIT ?",
            (decision_type, limit),
        ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def export_chain(
        self,
        session_id: str | None = None,
        decision_type: str | None = None,
    ) -> str:
        """Export audit chain as JSON for compliance reporting."""
        entries = self._fetch_entries(session_id=session_id, decision_type=decision_type)
        return json.dumps(
            [e.to_dict() for e in entries],
            indent=2,
            ensure_ascii=False,
        )

    def count_entries(self, session_id: str | None = None) -> int:
        """Count total audit entries, optionally filtered by session."""
        if session_id:
            row = self._conn.execute(
                "SELECT COUNT(*) as cnt FROM audit_entries WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        else:
            row = self._conn.execute("SELECT COUNT(*) as cnt FROM audit_entries").fetchone()
        return row["cnt"]

    def _fetch_entries(
        self,
        session_id: str | None = None,
        decision_type: str | None = None,
    ) -> list[AuditEntry]:
        query = "SELECT * FROM audit_entries WHERE 1=1"
        params: list[Any] = []
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        if decision_type:
            query += " AND decision_type = ?"
            params.append(decision_type)
        query += " ORDER BY timestamp DESC"
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def _persist_entry(self, entry: AuditEntry) -> None:
        self._conn.execute(
            """
            INSERT INTO audit_entries
            (id, timestamp, agent_id, session_id, decision_type,
             input_summary, output_summary, rationale, confidence, alternatives_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.id,
                entry.timestamp,
                entry.agent_id,
                entry.session_id,
                entry.decision_type,
                entry.input_summary,
                entry.output_summary,
                entry.rationale,
                entry.confidence,
                json.dumps(entry.alternatives_considered),
            ),
        )
        self._conn.commit()

    def _row_to_entry(self, row: sqlite3.Row) -> AuditEntry:
        return AuditEntry(
            id=row["id"],
            timestamp=row["timestamp"],
            agent_id=row["agent_id"],
            session_id=row["session_id"],
            decision_type=row["decision_type"],
            input_summary=row["input_summary"],
            output_summary=row["output_summary"],
            rationale=row["rationale"],
            confidence=row["confidence"],
            alternatives_considered=json.loads(row["alternatives_json"]),
        )

    def close(self) -> None:
        self._conn.close()

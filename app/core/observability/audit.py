"""Decision audit chain for compliance and traceability.

Every routing decision, tool selection, model switch, and security-enforcement
outcome is appended to the ``audit_entries`` table.

Durability contract
-------------------
The chain writes through the application's SQLAlchemy session onto the table
managed by Alembic (``alembic/versions`` creates ``audit_entries``). It opens
no connection of its own and creates no table of its own, so a decision
recorded here is immediately visible to any other reader of the same database
and survives process restarts.

Immutability is enforced by the schema: the migration installs
``BEFORE UPDATE`` / ``BEFORE DELETE`` triggers that abort the statement, so the
append-only promise in :class:`AuditEntry` is a database guarantee rather than
a convention.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    Index,
    String,
    Text,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from app.storage import Base
import app.storage as storage

logger = structlog.get_logger()


class AuditEntryRecord(Base):
    """ORM row for one immutable decision record."""

    __tablename__ = "audit_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    agent_id: Mapped[str] = mapped_column(String(100), nullable=False, default="", index=True)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, default="", index=True)
    decision_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    input_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    output_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    alternatives_considered: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    allowed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    subject: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_audit_entries_session_decision", "session_id", "decision_type"),
    )


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
    allowed: bool | None = None
    subject: str = ""

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
            "allowed": self.allowed,
            "subject": self.subject,
        }

    @classmethod
    def from_record(cls, record: AuditEntryRecord) -> AuditEntry:
        timestamp = record.timestamp
        if isinstance(timestamp, datetime):
            stamp = (
                timestamp.isoformat()
                if timestamp.tzinfo
                else timestamp.replace(tzinfo=UTC).isoformat()
            )
        else:
            stamp = str(timestamp)
        return cls(
            id=record.id,
            timestamp=stamp,
            agent_id=record.agent_id or "",
            session_id=record.session_id or "",
            decision_type=record.decision_type,
            input_summary=record.input_summary or "",
            output_summary=record.output_summary or "",
            rationale=record.rationale or "",
            confidence=float(record.confidence or 0.0),
            alternatives_considered=list(record.alternatives_considered or []),
            allowed=record.allowed,
            subject=record.subject or "",
        )


class AuditChain:
    """Append-only audit chain for decision tracking.

    Backed by the application's SQLAlchemy session, so records land in the
    Alembic-managed ``audit_entries`` table.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None):
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory or storage.async_session

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        return self._session_factory

    async def log_decision(
        self,
        decision_type: str,
        input_summary: str = "",
        output_summary: str = "",
        rationale: str = "",
        confidence: float = 0.0,
        alternatives_considered: list[str] | None = None,
        agent_id: str = "",
        session_id: str = "",
        allowed: bool | None = None,
        subject: str = "",
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
            allowed=allowed,
            subject=subject,
        )
        await self._persist_entry(entry)
        return entry

    async def log_security_decision(
        self,
        decision_type: str,
        *,
        allowed: bool,
        reason: str,
        subject: str = "",
        agent_id: str = "",
        session_id: str = "",
    ) -> AuditEntry:
        """Record an allow/deny outcome from an enforcement point."""
        return await self.log_decision(
            decision_type=decision_type,
            input_summary=subject[:2000],
            output_summary="allowed" if allowed else "denied",
            rationale=reason[:4000],
            agent_id=agent_id,
            session_id=session_id,
            allowed=allowed,
            subject=subject[:2000],
        )

    async def get_chain(
        self,
        limit: int = 100,
        offset: int = 0,
        session_id: str | None = None,
    ) -> list[AuditEntry]:
        """Retrieve audit entries, optionally filtered by session."""
        query = select(AuditEntryRecord)
        if session_id:
            query = query.where(AuditEntryRecord.session_id == session_id)
        query = query.order_by(AuditEntryRecord.timestamp.desc()).limit(limit).offset(offset)
        async with self._session_factory() as session:
            rows = (await session.execute(query)).scalars().all()
        return [AuditEntry.from_record(row) for row in rows]

    async def get_entry(self, entry_id: str) -> AuditEntry | None:
        """Retrieve a single audit entry by ID."""
        async with self._session_factory() as session:
            record = await session.get(AuditEntryRecord, entry_id)
        return AuditEntry.from_record(record) if record else None

    async def search_by_type(self, decision_type: str, limit: int = 50) -> list[AuditEntry]:
        """Search audit entries by decision type."""
        query = (
            select(AuditEntryRecord)
            .where(AuditEntryRecord.decision_type == decision_type)
            .order_by(AuditEntryRecord.timestamp.desc())
            .limit(limit)
        )
        async with self._session_factory() as session:
            rows = (await session.execute(query)).scalars().all()
        return [AuditEntry.from_record(row) for row in rows]

    async def export_chain(
        self,
        session_id: str | None = None,
        decision_type: str | None = None,
    ) -> str:
        """Export audit chain as JSON for compliance reporting."""
        import json

        entries = await self._fetch_entries(session_id=session_id, decision_type=decision_type)
        return json.dumps(
            [e.to_dict() for e in entries],
            indent=2,
            ensure_ascii=False,
        )

    async def count_entries(self, session_id: str | None = None) -> int:
        """Count total audit entries, optionally filtered by session."""
        query = select(func.count()).select_from(AuditEntryRecord)
        if session_id:
            query = query.where(AuditEntryRecord.session_id == session_id)
        async with self._session_factory() as session:
            return int((await session.execute(query)).scalar() or 0)

    async def _fetch_entries(
        self,
        session_id: str | None = None,
        decision_type: str | None = None,
    ) -> list[AuditEntry]:
        query = select(AuditEntryRecord)
        if session_id:
            query = query.where(AuditEntryRecord.session_id == session_id)
        if decision_type:
            query = query.where(AuditEntryRecord.decision_type == decision_type)
        query = query.order_by(AuditEntryRecord.timestamp.desc())
        async with self._session_factory() as session:
            rows = (await session.execute(query)).scalars().all()
        return [AuditEntry.from_record(row) for row in rows]

    async def _persist_entry(self, entry: AuditEntry) -> None:
        record = AuditEntryRecord(
            id=entry.id,
            timestamp=datetime.fromisoformat(entry.timestamp),
            agent_id=entry.agent_id,
            session_id=entry.session_id,
            decision_type=entry.decision_type,
            input_summary=entry.input_summary,
            output_summary=entry.output_summary,
            rationale=entry.rationale,
            confidence=entry.confidence,
            alternatives_considered=list(entry.alternatives_considered),
            allowed=entry.allowed,
            subject=entry.subject,
        )
        async with self._session_factory() as session:
            session.add(record)
            await session.commit()

    async def close(self) -> None:
        """No-op: the chain does not own its connection."""
        return None


# Process-wide chain used by enforcement points and the observability API.
audit_chain = AuditChain()

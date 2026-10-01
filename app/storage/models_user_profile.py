"""Durable storage for the user profile learning loop.

The in-memory ``ProfileLoopService`` keeps only the current process state, so
every Agent-internal interaction signal is appended to ``user_profile_events``
and can be replayed into a fresh service after a restart. The recomputed
summary is cached in ``user_profile_snapshots`` (one row per user) for audit
and fast reads. Verbatim instruction text is deliberately not stored here: it
already lives in ``user_instruction_traces`` and the profile layer only needs
the statistical fields.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.storage import Base


class UserProfileEvent(Base):
    """One Agent-internal interaction signal accepted by the profile loop."""

    __tablename__ = "user_profile_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    task_type: Mapped[str] = mapped_column(String(128), nullable=False)
    tool: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reasoning_level: Mapped[str] = mapped_column(String(32), nullable=False, default="standard")
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    feedback: Mapped[str | None] = mapped_column(String(16), nullable=True)
    interrupted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    retried: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "source IN ('agent_internal', 'instruction_trace')",
            name="ck_user_profile_events_source",
        ),
        CheckConstraint(
            "outcome IN ('success', 'failure')",
            name="ck_user_profile_events_outcome",
        ),
    )


class UserProfileSnapshot(Base):
    """Latest summary projection for one user, rewritten on every recomputation."""

    __tablename__ = "user_profile_snapshots"

    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

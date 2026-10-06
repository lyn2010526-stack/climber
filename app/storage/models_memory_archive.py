"""Persistent memory-archive models — L0/L1 sidecars and session archives.

Mirrors OpenViking's three-layer context model on our own storage:

- ``memory_sidecars``: directory-level semantic sidecars. Level 0 stores the
  short abstract (L0), level 1 the overview (L1). A (user, scope, level) pair
  is unique so a refresh upserts in place.
- ``session_archives``: structured conversation archives produced when a
  session commits, with a one-line summary and a memory-change diff.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.storage import Base


class MemorySidecar(Base):
    """Directory-level L0/L1 semantic sidecar (abstract/overview)."""

    __tablename__ = "memory_sidecars"
    __table_args__ = (
        UniqueConstraint("user_id", "scope", "level", name="uq_memory_sidecar_scope_level"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=abstract, 1=overview
    body: Mapped[str] = mapped_column(Text, nullable=False)

    generated_by: Mapped[str] = mapped_column(String(50), default="rule")
    sample_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    freshness: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
    )


class SessionArchive(Base):
    """Structured archive of a committed session plus its memory diff."""

    __tablename__ = "session_archives"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    one_line_summary: Mapped[str] = mapped_column(Text, default="")
    message_count: Mapped[int] = mapped_column(Integer, default=0)

    messages: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    memory_diff: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    archive_status: Mapped[str] = mapped_column(String(20), default="completed")

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

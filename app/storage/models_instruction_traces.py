"""Verbatim archive of every user instruction issued to the platform.

The trace store is the durable source of truth behind the instruction memory
feature: a single conversation context window is finite, so the raw wording of
each user instruction is written here verbatim and survives model swaps,
compaction and restarts. Parsing layers fill in ``intent_summary`` and
``task_spec`` afterwards; ``raw_text`` is never rewritten.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.storage import Base


class InstructionSource(StrEnum):
    """Where an instruction entered the system."""

    CHAT = "chat"
    API = "api"
    CLI = "cli"


class InstructionTrace(Base):
    """One archived user instruction.

    ``raw_text`` holds the instruction byte-for-byte as the user typed it and is
    never trimmed, normalised or rewritten. ``text_hash`` supports near-sink
    duplicate suppression: the same sentence re-sent within the dedup window is
    folded into the existing row instead of appending another copy.
    """

    __tablename__ = "user_instruction_traces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Ownership. Both stay nullable: a local single-user install has no user row
    # and an instruction can be issued before a session exists.
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Filled in by the parsing layer after the raw instruction is archived.
    intent_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_spec: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    goal_preserved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    source: Mapped[str] = mapped_column(
        String(20),
        default=InstructionSource.CHAT.value,
        nullable=False,
        index=True,
    )
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Incremental compression bookkeeping. A compressed-away row keeps its
    # raw_text and only gains a pointer to the summary record that absorbed it.
    compressed_into_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("user_instruction_traces.id"),
        nullable=True,
        index=True,
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "source IN ('chat', 'api', 'cli')",
            name="ck_user_instruction_traces_source",
        ),
        CheckConstraint("token_count >= 0", name="ck_user_instruction_traces_token_count"),
        CheckConstraint(
            "compressed_into_id IS NULL OR compressed_into_id <> id",
            name="ck_user_instruction_traces_compression_self",
        ),
        Index("ix_user_instruction_traces_session_created", "session_id", "created_at"),
        Index("ix_user_instruction_traces_user_created", "user_id", "created_at"),
        Index("ix_user_instruction_traces_hash_created", "text_hash", "created_at"),
    )

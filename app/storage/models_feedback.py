"""Feedback data model for user ratings on messages."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.storage import Base


class Rating(StrEnum):
    UP = "up"
    DOWN = "down"


class FeedbackReason(StrEnum):
    FACTUAL_ERROR = "factual_error"
    FORMAT = "format"
    INCOMPLETE = "incomplete"
    IRRELEVANT = "irrelevant"
    OTHER = "other"


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (
        UniqueConstraint("message_id", "user_id", name="uq_feedback_message_user"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    message_id: Mapped[str] = mapped_column(String(36), ForeignKey("messages.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    rating: Mapped[str] = mapped_column(String(10), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(20), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

"""Reasoning-specific database models."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, Float, Integer, JSON, String, Text, ForeignKey, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.storage import Base


class ReasoningTraceDB(Base):
    """Persistent reasoning trace."""

    __tablename__ = "reasoning_traces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    trace_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    task: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(50), nullable=False)
    candidates_count: Mapped[int] = mapped_column(Integer, default=0)
    best_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    coverage_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    path_traces: Mapped[list[Any]] = mapped_column(JSON, default=list)
    coverage_report: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ReasoningFeedbackDB(Base):
    """User feedback on reasoning results."""

    __tablename__ = "reasoning_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    trace_id: Mapped[str] = mapped_column(String(36), ForeignKey("reasoning_traces.trace_id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    thumbs: Mapped[str | None] = mapped_column(String(10), nullable=True)
    comment: Mapped[str] = mapped_column(Text, default="")
    selected_candidate_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

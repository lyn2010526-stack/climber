"""Cost tracking and budget models."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.storage import Base


class CostRecord(Base):
    """Record of LLM usage cost per API call."""

    __tablename__ = "cost_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True, default="default-user")
    session_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("sessions.id"), nullable=True, index=True)

    # Model info
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Token usage
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)

    # Cost
    input_cost: Mapped[float] = mapped_column(Float, default=0.0)
    output_cost: Mapped[float] = mapped_column(Float, default=0.0)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class BudgetConfig(Base):
    """User budget configuration."""

    __tablename__ = "budget_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, unique=True, default="default-user")

    # Budget settings
    amount: Mapped[float] = mapped_column(Float, default=10.0)  # Default $10/month
    period: Mapped[str] = mapped_column(String(20), default="monthly")  # daily, weekly, monthly
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)

    # Limits
    per_session_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    per_request_limit: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class UsageQuota(Base):
    """Track per-user usage quotas (requests, tokens)."""

    __tablename__ = "usage_quotas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, unique=True, default="default-user")

    # Quota limits
    max_requests_per_day: Mapped[int] = mapped_column(Integer, default=100)
    max_tokens_per_day: Mapped[int] = mapped_column(Integer, default=100_000)
    max_cost_per_month: Mapped[float] = mapped_column(Float, default=10.0)

    # Current usage (reset periodically)
    requests_today: Mapped[int] = mapped_column(Integer, default=0)
    tokens_today: Mapped[int] = mapped_column(Integer, default=0)
    cost_this_month: Mapped[float] = mapped_column(Float, default=0.0)

    # Reset tracking
    last_reset_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_reset_month: Mapped[str] = mapped_column(String(7), default="")  # YYYY-MM

    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

"""Evaluation framework data models."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
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


class EvalDataset(Base):
    """A dataset of test cases for agent evaluation."""

    __tablename__ = "eval_datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True, default="default-user")

    # Dataset content (JSON array of cases)
    case_count: Mapped[int] = mapped_column(Integer, default=0)
    data_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EvalRun(Base):
    """A single evaluation run against a dataset."""

    __tablename__ = "eval_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("eval_datasets.id"), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True, default="default-user")

    # Results summary
    total_cases: Mapped[int] = mapped_column(Integer, default=0)
    passed_cases: Mapped[int] = mapped_column(Integer, default=0)
    failed_cases: Mapped[int] = mapped_column(Integer, default=0)
    average_score: Mapped[float] = mapped_column(Float, default=0.0)
    pass_rate: Mapped[float] = mapped_column(Float, default=0.0)

    # Detailed results
    results_json: Mapped[str] = mapped_column(Text, default="[]")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EvalResult(Base):
    """Individual case result within an eval run.

    Kept for detailed per-case analysis.
    """

    __tablename__ = "eval_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("eval_runs.id"), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # Scoring
    score: Mapped[float] = mapped_column(Float, default=0.0)
    passed: Mapped[bool] = mapped_column(Integer, default=0)  # 0 or 1
    actual_output: Mapped[str] = mapped_column(Text, default="")
    reasoning: Mapped[str] = mapped_column(Text, default="")

    # Metadata
    scoring_method: Mapped[str] = mapped_column(String(30), default="contains")
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

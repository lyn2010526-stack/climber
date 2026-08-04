"""Skill versioning and testing models."""

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


class SkillVersion(Base):
    """Version history for a skill's prompt and tools."""

    __tablename__ = "skill_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    skill_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(20), nullable=False)

    # Version content
    prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tools: Mapped[list[str]] = mapped_column(Text, default="[]")  # JSON array

    # Metadata
    author: Mapped[str] = mapped_column(String(100), default="system")
    changelog: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SkillTestCase(Base):
    """Test case for verifying skill behavior."""

    __tablename__ = "skill_test_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    skill_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Test definition
    input_params: Mapped[str] = mapped_column(Text, default="{}")  # JSON
    expected_output_contains: Mapped[str] = mapped_column(Text, default="")
    expected_tools: Mapped[list[str]] = mapped_column(Text, default="[]")  # JSON array
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SkillTestResult(Base):
    """Result of running a skill test case."""

    __tablename__ = "skill_test_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    test_id: Mapped[str] = mapped_column(String(36), ForeignKey("skill_test_cases.id"), nullable=False, index=True)
    skill_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Result
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    actual_output: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

"""Trace span records for observability."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
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


class TraceSpanRecord(Base):
    """Database record for a trace span.

    Stores key metrics and summaries for observability.
    Full content is truncated to keep storage manageable.
    """

    __tablename__ = "trace_spans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    parent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("trace_spans.id"), nullable=True, index=True)

    # Span metadata
    kind: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ok")
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    # Performance metrics
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Content summaries (truncated)
    input_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column("metadata", Text, nullable=True)

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "id": self.id,
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "kind": self.kind,
            "name": self.name,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "tokens_used": self.tokens_used,
            "model": self.model,
            "tool_name": self.tool_name,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "metadata": self.metadata_json,
        }

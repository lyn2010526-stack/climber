"""OpenTelemetry tracing — LangSmith-style observability.

Provides:
- Distributed tracing for LLM calls, tool executions, and agent loops
- Span hierarchy: AgentSession > LLM Call > Tool Execution
- Export to console (dev) and OTLP (production)
- Trace storage in PostgreSQL for historical analysis
"""

from __future__ import annotations

import json
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any
from enum import Enum

import structlog
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage import async_session

logger = structlog.get_logger()


class SpanStatus(str, Enum):
    OK = "ok"
    ERROR = "error"
    CANCELLED = "cancelled"


class SpanKind(str, Enum):
    AGENT_SESSION = "agent_session"
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    REVIEW = "review"
    WORKFLOW = "workflow"
    MEMORY = "memory"
    RAG = "rag"
    CUSTOM = "custom"


class TraceStore:
    """PostgreSQL-backed trace storage.

    Stores spans for later retrieval and analysis.
    Lightweight — only stores key metrics, not full content.
    """

    async def save_span(self, span: "Span") -> str:
        """Persist a completed span."""
        try:
            async with async_session() as db:
                from app.storage.models_traces import TraceSpanRecord
                record = TraceSpanRecord(
                    id=span.id,
                    trace_id=span.trace_id,
                    parent_id=span.parent_id,
                    kind=span.kind.value,
                    name=span.name,
                    status=span.status.value,
                    duration_ms=span.duration_ms,
                    input_summary=span.input_summary[:2000] if span.input_summary else None,
                    output_summary=span.output_summary[:2000] if span.output_summary else None,
                    error=span.error[:1000] if span.error else None,
                    tokens_used=span.tokens_used,
                    model=span.model,
                    tool_name=span.tool_name,
                    metadata_json=json.dumps(span.metadata, ensure_ascii=False) if span.metadata else None,
                )
                db.add(record)
                await db.commit()
                return record.id
        except Exception as e:
            logger.error("Failed to save trace span", error=str(e))
            return ""

    async def get_trace(self, trace_id: str) -> list[dict]:
        """Get all spans for a trace."""
        async with async_session() as db:
            from app.storage.models_traces import TraceSpanRecord
            result = await db.execute(
                select(TraceSpanRecord)
                .where(TraceSpanRecord.trace_id == trace_id)
                .order_by(TraceSpanRecord.started_at)
            )
            spans = result.scalars().all()
            return [s.to_dict() for s in spans]

    async def list_traces(
        self,
        user_id: str | None = None,
        limit: int = 50,
        kind: str | None = None,
    ) -> list[dict]:
        """List traces with filtering."""
        async with async_session() as db:
            from app.storage.models_traces import TraceSpanRecord
            query = select(TraceSpanRecord).where(TraceSpanRecord.parent_id == None)
            if user_id:
                query = query.where(TraceSpanRecord.user_id == user_id)
            if kind:
                query = query.where(TraceSpanRecord.kind == kind)
            query = query.order_by(desc(TraceSpanRecord.started_at)).limit(limit)
            result = await db.execute(query)
            spans = result.scalars().all()
            return [s.to_dict() for s in spans]

    async def get_trace_stats(self, trace_id: str) -> dict:
        """Get aggregate statistics for a trace."""
        async with async_session() as db:
            from app.storage.models_traces import TraceSpanRecord
            result = await db.execute(
                select(TraceSpanRecord).where(TraceSpanRecord.trace_id == trace_id)
            )
            spans = result.scalars().all()
            if not spans:
                return {}

            total_duration = sum(s.duration_ms for s in spans)
            total_tokens = sum(s.tokens_used or 0 for s in spans)
            error_count = sum(1 for s in spans if s.status == SpanStatus.ERROR.value)
            llm_calls = sum(1 for s in spans if s.kind == SpanKind.LLM_CALL.value)
            tool_calls = sum(1 for s in spans if s.kind == SpanKind.TOOL_CALL.value)

            return {
                "trace_id": trace_id,
                "total_spans": len(spans),
                "total_duration_ms": total_duration,
                "total_tokens": total_tokens,
                "error_count": error_count,
                "llm_calls": llm_calls,
                "tool_calls": tool_calls,
            }


class Span:
    """A single trace span representing a unit of work.

    Lightweight alternative to full OpenTelemetry SDK — captures the
    essential tracing data without external dependencies.
    """

    def __init__(
        self,
        name: str,
        kind: SpanKind,
        trace_id: str | None = None,
        parent_id: str | None = None,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.id = str(uuid.uuid4())[:16]
        self.trace_id = trace_id or str(uuid.uuid4())
        self.parent_id = parent_id
        self.name = name
        self.kind = kind
        self.status = SpanStatus.OK
        self.user_id = user_id
        self.metadata = metadata or {}

        self.start_time = time.monotonic()
        self.end_time: float | None = None
        self.duration_ms: float = 0.0

        self.input_summary: str | None = None
        self.output_summary: str | None = None
        self.error: str | None = None
        self.tokens_used: int = 0
        self.model: str | None = None
        self.tool_name: str | None = None

    def set_input(self, data: Any) -> None:
        """Set input summary (truncated)."""
        try:
            text = json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data
            self.input_summary = text[:2000]
        except Exception:
            self.input_summary = str(data)[:2000]

    def set_output(self, data: Any) -> None:
        """Set output summary (truncated)."""
        try:
            text = json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data
            self.output_summary = text[:2000]
        except Exception:
            self.output_summary = str(data)[:2000]

    def set_error(self, error: str) -> None:
        """Record an error."""
        self.status = SpanStatus.ERROR
        self.error = str(error)[:1000]

    def set_tokens(self, count: int, model: str | None = None) -> None:
        """Record token usage."""
        self.tokens_used = count
        if model:
            self.model = model

    def finish(self) -> None:
        """Mark span as complete."""
        self.end_time = time.monotonic()
        self.duration_ms = (self.end_time - self.start_time) * 1000

    async def __aenter__(self) -> "Span":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_val:
            self.set_error(str(exc_val))
        self.finish()
        # Persist to DB
        store = TraceStore()
        await store.save_span(self)

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "id": self.id,
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "kind": self.kind.value,
            "status": self.status.value,
            "duration_ms": round(self.duration_ms, 2),
            "tokens_used": self.tokens_used,
            "model": self.model,
            "error": self.error,
            "metadata": self.metadata,
        }


class TracingContext:
    """Context manager for creating span hierarchies.

    Usage:
        async with TracingContext("agent_session", user_id="123") as root:
            async with root.child_span("llm_call", SpanKind.LLM_CALL) as span:
                span.set_input(messages)
                result = await model.chat(messages)
                span.set_output(result)
    """

    def __init__(
        self,
        name: str,
        kind: SpanKind = SpanKind.AGENT_SESSION,
        user_id: str | None = None,
        trace_id: str | None = None,
        parent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.span = Span(name, kind, trace_id=trace_id, parent_id=parent_id, user_id=user_id, metadata=metadata)
        self._child_trace_id = self.span.trace_id

    async def __aenter__(self) -> "TracingContext":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_val:
            self.span.set_error(str(exc_val))
        self.span.finish()
        store = TraceStore()
        await store.save_span(self.span)

    @asynccontextmanager
    async def child_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.CUSTOM,
        metadata: dict[str, Any] | None = None,
    ):
        """Create a child span within this context."""
        child = Span(
            name, kind,
            trace_id=self._child_trace_id,
            parent_id=self.span.id,
            user_id=self.span.user_id,
            metadata=metadata,
        )
        try:
            yield child
        except Exception as e:
            child.set_error(str(e))
            raise
        finally:
            child.finish()
            store = TraceStore()
            await store.save_span(child)


# Global trace store
trace_store = TraceStore()

"""Tracing middleware — automatic observability for middleware and tool execution.

Uses the event bus to automatically trace:
- Middleware hook execution
- Tool call lifecycle
- Session lifecycle
- Performance metrics
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import structlog

from app.core.event_bus import get_event_bus
from app.core.middleware import MiddlewareBase

if TYPE_CHECKING:
    from app.core.agent_engine import AgentEngine, AgentSession

logger = structlog.get_logger()


class TracingMiddleware(MiddlewareBase):
    """Middleware that provides automatic tracing via the event bus.

    Features:
    - Traces all middleware hook execution times
    - Records tool call performance metrics
    - Tracks session lifecycle events
    - Emits structured logs for debugging
    """

    def __init__(self, emit_events: bool = True, log_level: str = "info"):
        self.emit_events = emit_events
        self.log_level = log_level
        self._active_spans: dict[str, float] = {}

    def _start_span(self, span_id: str, name: str) -> None:
        """Start a timing span."""
        self._active_spans[span_id] = time.monotonic()

    def _end_span(self, span_id: str) -> float:
        """End a timing span and return duration in ms."""
        start = self._active_spans.pop(span_id, time.monotonic())
        return (time.monotonic() - start) * 1000

    async def on_reasoning(
        self,
        engine: AgentEngine,
        session: AgentSession,
        input_kwargs: dict[str, Any],
        next_handler: Any,
    ) -> Any:
        """Trace reasoning phase."""
        span_id = f"reasoning_{session.session_id}_{input_kwargs.get('iteration', 0)}"
        self._start_span(span_id, "reasoning")

        if self.emit_events:
            await get_event_bus().publish("middleware_start", {
                "hook": "on_reasoning",
                "session_id": session.session_id,
                "iteration": input_kwargs.get("iteration", 0),
            })

        try:
            async for event in next_handler():
                yield event
        finally:
            duration = self._end_span(span_id)
            if self.emit_events:
                await get_event_bus().publish("middleware_end", {
                    "hook": "on_reasoning",
                    "session_id": session.session_id,
                    "duration_ms": duration,
                })
            if self.log_level == "debug":
                logger.debug("tracing.reasoning_completed", duration_ms=duration)

    async def on_acting(
        self,
        engine: AgentEngine,
        session: AgentSession,
        input_kwargs: dict[str, Any],
        next_handler: Any,
    ) -> Any:
        """Trace acting phase."""
        span_id = f"acting_{session.session_id}_{time.monotonic()}"
        self._start_span(span_id, "acting")

        if self.emit_events:
            tool_calls = input_kwargs.get("tool_calls", [])
            await get_event_bus().publish("middleware_start", {
                "hook": "on_acting",
                "session_id": session.session_id,
                "tool_count": len(tool_calls),
            })

        try:
            async for event in next_handler():
                yield event
        finally:
            duration = self._end_span(span_id)
            if self.emit_events:
                await get_event_bus().publish("middleware_end", {
                    "hook": "on_acting",
                    "session_id": session.session_id,
                    "duration_ms": duration,
                })
            if self.log_level == "debug":
                logger.debug("tracing.acting_completed", duration_ms=duration)

    async def on_compress_context(
        self,
        engine: AgentEngine,
        session: AgentSession,
        input_kwargs: dict[str, Any],
        next_handler: Any,
    ) -> None:
        """Trace context compression."""
        span_id = f"compress_{session.session_id}_{time.monotonic()}"
        self._start_span(span_id, "compress_context")

        if self.emit_events:
            await get_event_bus().publish("middleware_start", {
                "hook": "on_compress_context",
                "session_id": session.session_id,
            })

        try:
            await next_handler()
        finally:
            duration = self._end_span(span_id)
            if self.emit_events:
                await get_event_bus().publish("middleware_end", {
                    "hook": "on_compress_context",
                    "session_id": session.session_id,
                    "duration_ms": duration,
                })

    async def on_check_permission(
        self,
        engine: AgentEngine,
        session: AgentSession,
        input_kwargs: dict[str, Any],
        next_handler: Any,
    ) -> tuple[bool, str]:
        """Trace permission check."""
        span_id = f"permission_{session.session_id}_{time.monotonic()}"
        self._start_span(span_id, "check_permission")

        tool_name = input_kwargs.get("tool_name", "unknown")

        try:
            result = await next_handler()
            duration = self._end_span(span_id)

            if self.emit_events:
                await get_event_bus().publish("permission_check", {
                    "session_id": session.session_id,
                    "tool_name": tool_name,
                    "allowed": result[0],
                    "duration_ms": duration,
                })

            return result
        except Exception as e:
            duration = self._end_span(span_id)
            if self.emit_events:
                await get_event_bus().publish("permission_error", {
                    "session_id": session.session_id,
                    "tool_name": tool_name,
                    "error": str(e),
                    "duration_ms": duration,
                })
            raise

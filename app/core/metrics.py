"""Metrics collection for agent operations.

Collects and exports:
- Iteration counts and durations
- Token usage per session
- Tool call success/failure rates
- API latency percentiles
- Error rates by type
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SessionMetrics:
    """Metrics for a single session."""
    session_id: str
    start_time: float = field(default_factory=time.monotonic)
    end_time: float | None = None
    iteration_count: int = 0
    tool_calls: int = 0
    tool_failures: int = 0
    token_input: int = 0
    token_output: int = 0
    api_calls: int = 0
    api_errors: int = 0
    total_duration_ms: float = 0
    errors: list[dict] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.tool_calls == 0:
            return 1.0
        return (self.tool_calls - self.tool_failures) / self.tool_calls

    @property
    def total_tokens(self) -> int:
        return self.token_input + self.token_output


@dataclass
class GlobalMetrics:
    """Aggregate metrics across all sessions."""
    total_sessions: int = 0
    active_sessions: int = 0
    total_iterations: int = 0
    total_tool_calls: int = 0
    total_tool_failures: int = 0
    total_api_calls: int = 0
    total_api_errors: int = 0
    total_tokens: int = 0
    total_errors: int = 0

    # Latency tracking (ms)
    api_latencies: list[float] = field(default_factory=list)

    @property
    def api_success_rate(self) -> float:
        if self.total_api_calls == 0:
            return 1.0
        return (self.total_api_calls - self.total_api_errors) / self.total_api_calls

    @property
    def tool_success_rate(self) -> float:
        if self.total_tool_calls == 0:
            return 1.0
        return (self.total_tool_calls - self.total_tool_failures) / self.total_tool_calls

    @property
    def avg_api_latency_ms(self) -> float:
        if not self.api_latencies:
            return 0.0
        return sum(self.api_latencies) / len(self.api_latencies)

    @property
    def p95_api_latency_ms(self) -> float:
        if not self.api_latencies:
            return 0.0
        sorted_latencies = sorted(self.api_latencies)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]


class MetricsCollector:
    """Collects and aggregates metrics across sessions."""

    def __init__(self):
        self._sessions: dict[str, SessionMetrics] = {}
        self._global = GlobalMetrics()

    def start_session(self, session_id: str):
        """Start tracking a session."""
        self._sessions[session_id] = SessionMetrics(session_id=session_id)
        self._global.total_sessions += 1
        self._global.active_sessions += 1

    def end_session(self, session_id: str):
        """End tracking a session."""
        if session_id in self._sessions:
            self._sessions[session_id].end_time = time.monotonic()
            self._global.active_sessions -= 1

    def record_iteration(self, session_id: str):
        """Record an iteration."""
        sess = self._sessions.setdefault(session_id, SessionMetrics(session_id=session_id))
        sess.iteration_count += 1
        self._global.total_iterations += 1

    def record_tool_call(self, session_id: str, success: bool):
        """Record a tool call."""
        sess = self._sessions.setdefault(session_id, SessionMetrics(session_id=session_id))
        sess.tool_calls += 1
        self._global.total_tool_calls += 1
        if not success:
            sess.tool_failures += 1
            self._global.total_tool_failures += 1

    def record_api_call(self, session_id: str, latency_ms: float, error: bool = False):
        """Record an API call."""
        sess = self._sessions.setdefault(session_id, SessionMetrics(session_id=session_id))
        sess.api_calls += 1
        self._global.total_api_calls += 1
        self._global.api_latencies.append(latency_ms)

        if error:
            sess.api_errors += 1
            self._global.total_api_errors += 1

    def record_tokens(self, session_id: str, input_tokens: int, output_tokens: int):
        """Record token usage."""
        sess = self._sessions.setdefault(session_id, SessionMetrics(session_id=session_id))
        sess.token_input += input_tokens
        sess.token_output += output_tokens
        self._global.total_tokens += input_tokens + output_tokens

    def record_error(self, session_id: str, error_type: str, message: str):
        """Record an error."""
        sess = self._sessions.setdefault(session_id, SessionMetrics(session_id=session_id))
        sess.errors.append({
            "type": error_type,
            "message": message,
            "time": time.monotonic(),
        })
        self._global.total_errors += 1

    def get_session_metrics(self, session_id: str) -> SessionMetrics | None:
        return self._sessions.get(session_id)

    def get_global_metrics(self) -> GlobalMetrics:
        return self._global

    def get_snapshot(self) -> dict:
        """Get a snapshot of all metrics."""
        return {
            "global": {
                "total_sessions": self._global.total_sessions,
                "active_sessions": self._global.active_sessions,
                "total_iterations": self._global.total_iterations,
                "tool_success_rate": self._global.tool_success_rate,
                "api_success_rate": self._global.api_success_rate,
                "avg_api_latency_ms": self._global.avg_api_latency_ms,
                "p95_api_latency_ms": self._global.p95_api_latency_ms,
                "total_tokens": self._global.total_tokens,
                "total_errors": self._global.total_errors,
            },
            "sessions": {
                sid: {
                    "iterations": s.iteration_count,
                    "tool_calls": s.tool_calls,
                    "success_rate": s.success_rate,
                    "total_tokens": s.total_tokens,
                }
                for sid, s in self._sessions.items()
            },
        }


# Singleton
metrics = MetricsCollector()

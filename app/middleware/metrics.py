"""Prometheus metrics for observability."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, Info, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

# Request metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

# Agent metrics
AGENT_RUN_TOTAL = Counter(
    "agent_runs_total",
    "Total agent runs",
    ["provider", "model_id", "status"],
)

AGENT_ITERATION_COUNT = Histogram(
    "agent_iterations",
    "Agent loop iterations per run",
    buckets=[1, 2, 5, 10, 15, 20, 25, 30],
)

TOOL_CALL_TOTAL = Counter(
    "tool_calls_total",
    "Total tool calls",
    ["tool_name", "status"],
)

TOOL_CALL_LATENCY = Histogram(
    "tool_call_duration_seconds",
    "Tool call latency",
    ["tool_name"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

# Token metrics
TOKEN_USAGE = Counter(
    "token_usage_total",
    "Token usage",
    ["provider", "model_id", "type"],  # Values: prompt/completion/total
)

# Active sessions
ACTIVE_SESSIONS = Gauge(
    "active_sessions",
    "Number of active sessions",
)

# App info
APP_INFO = Info(
    "agent_engine",
    "Application information",
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect request metrics."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start_time = time.time()
        method = request.method
        path = request.url.path

        response = await call_next(request)

        duration = time.time() - start_time
        status = str(response.status_code)

        REQUEST_COUNT.labels(method=method, endpoint=path, status=status).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=path).observe(duration)

        return response


async def metrics_endpoint() -> Response:
    """Expose Prometheus metrics."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )

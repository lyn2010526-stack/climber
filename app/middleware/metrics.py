"""Prometheus metrics for observability."""

from __future__ import annotations

import time
from typing import Any

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
    ["provider", "model_id", "type"],  # type: prompt/completion/total
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

    async def dispatch(self, request: Request, call_next):
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


def record_token_usage(
    provider: str,
    model_id: str,
    usage: dict[str, Any] | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
) -> None:
    """Increment the token counters from a model response.

    TOKEN_USAGE was declared and exported but never written to, so
    `token_usage_total` sat at zero on /metrics. This is the write point.

    Every failure mode is swallowed: a metrics path must never turn a
    successful model response into a failed request, and a provider that
    reports no usage is normal rather than exceptional.

    Args:
        provider: Model provider name, used as a label.
        model_id: Model identifier, used as a label.
        usage: The provider's usage mapping, if one was returned.
        prompt_tokens: Prompt token count, when not carried in `usage`.
        completion_tokens: Completion token count, when not in `usage`.
        total_tokens: Total token count, when not in `usage`.
    """
    if not model_id:
        return

    prompt = _as_token_count(
        prompt_tokens if prompt_tokens is not None else (usage or {}).get("prompt_tokens")
    )
    completion = _as_token_count(
        completion_tokens
        if completion_tokens is not None
        else (usage or {}).get("completion_tokens")
    )
    total = _as_token_count(
        total_tokens if total_tokens is not None else (usage or {}).get("total_tokens")
    )

    try:
        if prompt is not None:
            TOKEN_USAGE.labels(
                provider=provider or "unknown",
                model_id=model_id,
                type="prompt",
            ).inc(prompt)
        if completion is not None:
            TOKEN_USAGE.labels(
                provider=provider or "unknown",
                model_id=model_id,
                type="completion",
            ).inc(completion)
        if total is not None:
            TOKEN_USAGE.labels(
                provider=provider or "unknown",
                model_id=model_id,
                type="total",
            ).inc(total)
    except Exception:  # pragma: no cover - metrics must never break a request
        return


def record_chat_result(result: Any, provider: str, model_id: str) -> None:
    """Record token usage straight from a ChatResult.

    Args:
        result: A ChatResult carrying a `usage` mapping.
        provider: Model provider name.
        model_id: Model identifier.
    """
    usage = getattr(result, "usage", None)
    if not usage:
        return
    record_token_usage(provider=provider, model_id=model_id, usage=usage)


def _as_token_count(value: Any) -> float | None:
    """Coerce a reported token count, rejecting anything unusable."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number < 0:
        return None
    return number

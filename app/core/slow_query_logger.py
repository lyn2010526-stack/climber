"""Slow query logging via SQLAlchemy event listeners.

Logs queries that exceed a configurable threshold (default 100ms).
Useful for identifying N+1 patterns and performance bottlenecks.
"""

from __future__ import annotations

import time

import structlog
from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = structlog.get_logger()

# Configurable threshold in milliseconds
SLOW_QUERY_THRESHOLD_MS = 100

_query_start_times: dict[int, float] = {}


@event.listens_for(Engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    _query_start_times[id(context)] = time.perf_counter()


@event.listens_for(Engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    start = _query_start_times.pop(id(context), None)
    if start is None:
        return
    duration_ms = (time.perf_counter() - start) * 1000

    if duration_ms >= SLOW_QUERY_THRESHOLD_MS:
        # Truncate statement for readability
        stmt_preview = statement[:300].replace("\n", " ").strip()
        if len(statement) > 300:
            stmt_preview += "..."
        logger.warning(
            "slow_query_detected",
            duration_ms=round(duration_ms, 2),
            threshold_ms=SLOW_QUERY_THRESHOLD_MS,
            statement=stmt_preview,
        )

    # Also record to Prometheus if available
    try:
        from app.middleware.metrics import REQUEST_LATENCY
        REQUEST_LATENCY.labels(method="DB", endpoint="query").observe(duration_ms / 1000)
    except Exception:
        pass


def install(threshold_ms: int = 100) -> None:
    """Install slow query logging with a custom threshold."""
    global SLOW_QUERY_THRESHOLD_MS
    SLOW_QUERY_THRESHOLD_MS = threshold_ms
    logger.info("slow_query_logger_installed", threshold_ms=threshold_ms)

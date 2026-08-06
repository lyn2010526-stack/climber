"""Structured logging with JSON output and correlation IDs.

Features:
- JSON-formatted log output for machine parsing
- Correlation IDs for tracing requests across async boundaries
- Proper log levels (DEBUG, INFO, WARN, ERROR)
- Context injection (session_id, agent_id, iteration)
- Performance timing helpers
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from contextvars import ContextVar
from functools import wraps

import structlog

# Context variables for correlation
correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")
session_ctx: ContextVar[str] = ContextVar("session_id", default="")
agent_ctx: ContextVar[str] = ContextVar("agent_id", default="")


def setup_logging(level: str = "INFO", json_format: bool = True):
    """Configure structured logging for the application."""
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, level.upper()),
    )

    if json_format:
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.dev.set_exc_info,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper())),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.dev.set_exc_info,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper())),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger with context."""
    return structlog.get_logger(name)


def set_correlation(corr_id: str | None = None) -> str:
    """Set correlation ID for current context."""
    cid = corr_id or str(uuid.uuid4())[:12]
    correlation_id.set(cid)
    return cid


def set_context(session_id: str = "", agent_id: str = ""):
    """Set session and agent context."""
    if session_id:
        session_ctx.set(session_id)
    if agent_id:
        agent_ctx.set(agent_id)


def clear_context():
    """Clear all context variables."""
    correlation_id.set("")
    session_ctx.set("")
    agent_ctx.set("")


class LogTimer:
    """Context manager for timing operations."""

    def __init__(self, logger: structlog.BoundLogger, operation: str, **extra):
        self.logger = logger
        self.operation = operation
        self.extra = extra
        self.start_time: float = 0

    def __enter__(self):
        self.start_time = time.monotonic()
        self.logger.info("operation_started", operation=self.operation, **self.extra)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = (time.monotonic() - self.start_time) * 1000
        if exc_type:
            self.logger.error(
                "operation_failed",
                operation=self.operation,
                elapsed_ms=round(elapsed, 2),
                error=str(exc_val),
                **self.extra,
            )
        else:
            self.logger.info(
                "operation_completed",
                operation=self.operation,
                elapsed_ms=round(elapsed, 2),
                **self.extra,
            )
        return False


def log_execution(logger_name: str = ""):
    """Decorator for logging function execution."""
    def decorator(func):
        logger = get_logger(logger_name or func.__module__)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.monotonic()
            try:
                result = await func(*args, **kwargs)
                elapsed = (time.monotonic() - start) * 1000
                logger.info(
                    "function_completed",
                    function=func.__name__,
                    elapsed_ms=round(elapsed, 2),
                )
                return result
            except Exception as e:
                elapsed = (time.monotonic() - start) * 1000
                logger.error(
                    "function_failed",
                    function=func.__name__,
                    elapsed_ms=round(elapsed, 2),
                    error=str(e),
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.monotonic()
            try:
                result = func(*args, **kwargs)
                elapsed = (time.monotonic() - start) * 1000
                logger.info(
                    "function_completed",
                    function=func.__name__,
                    elapsed_ms=round(elapsed, 2),
                )
                return result
            except Exception as e:
                elapsed = (time.monotonic() - start) * 1000
                logger.error(
                    "function_failed",
                    function=func.__name__,
                    elapsed_ms=round(elapsed, 2),
                    error=str(e),
                )
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator

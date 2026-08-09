"""Resilience primitives for the agent engine.

Provides:
- CircuitBreaker: CLOSED -> OPEN -> HALF_OPEN state machine
- RetryHandler: retryable exception handling with exponential backoff
- ResourceTracker: async cleanup registry
- TimeoutConfig and timeout errors
- SessionMetrics: per-session operational metrics
"""

from __future__ import annotations

import asyncio
import inspect
import random
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.core.exceptions import AgentEngineError

# ── Errors ───────────────────────────────────────────────────────────────


class CircuitBreakerOpenError(AgentEngineError):
    """Raised when a circuit breaker is open and blocks a call."""


class SessionTimeoutError(AgentEngineError):
    """Raised when the overall session deadline is exceeded."""


class IterationTimeoutError(AgentEngineError):
    """Raised when a single iteration deadline is exceeded."""


class RetryExhaustedError(AgentEngineError):
    """Raised when all retry attempts for an operation have been exhausted."""


# ── Circuit Breaker ─────────────────────────────────────────────────────


class CircuitState(StrEnum):
    """States of a circuit breaker."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker."""

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 1


class CircuitBreaker:
    """Protects downstream calls by tripping open after repeated failures.

    States:
    - CLOSED: normal operation, requests pass through
    - OPEN: failure threshold exceeded, requests blocked
    - HALF_OPEN: testing if the service recovered (limited probe calls)
    """

    def __init__(self, name: str, config: CircuitBreakerConfig | None = None) -> None:
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_used = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> CircuitState:
        if (
            self._state == CircuitState.OPEN
            and self._opened_at is not None
            and time.monotonic() - self._opened_at >= self.config.recovery_timeout
        ):
            self._state = CircuitState.HALF_OPEN
            self._half_open_used = 0
        return self._state

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    @property
    def failure_count(self) -> int:
        return self._failure_count

    async def call(self, coro: Any) -> Any:
        """Execute a call through the circuit breaker.

        Args:
            coro: A coroutine function or an awaitable to execute.

        Returns:
            The result of the call.

        Raises:
            CircuitBreakerOpenError: If the breaker is open or half-open capacity is exhausted.
        """
        current = self.state
        if current == CircuitState.OPEN:
            raise CircuitBreakerOpenError(f"circuit_breaker '{self.name}' is open")
        if current == CircuitState.HALF_OPEN:
            if self._half_open_used >= self.config.half_open_max_calls:
                raise CircuitBreakerOpenError(f"circuit_breaker '{self.name}' half-open capacity reached")
            self._half_open_used += 1
        try:
            if inspect.isawaitable(coro):
                result = await coro
            else:
                result = await coro()
        except BaseException as e:
            self._record_failure()
            raise e
        self._record_success()
        return result

    def _record_failure(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()
            return
        self._failure_count += 1
        if self._failure_count >= self.config.failure_threshold:
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()

    def _record_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._opened_at = None
            return
        self._failure_count = 0

    def reset(self) -> None:
        """Force the breaker back to the CLOSED state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_used = 0
        self._opened_at = None


# ── Retry Handler ───────────────────────────────────────────────────────


@dataclass
class RetryConfig:
    """Configuration for retry behaviour."""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    jitter: bool = True


class RetryHandler:
    """Executes a call with retries for retryable exceptions."""

    def __init__(self, config: RetryConfig) -> None:
        self.config = config

    def _is_retryable(self, exc: BaseException) -> bool:
        if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
            return True
        status = getattr(exc, "status_code", None)
        if status is not None:
            try:
                code = int(status)
            except (TypeError, ValueError):
                return False
            if code >= 429:
                return True
        return False

    def _calculate_delay(self, attempt: int) -> float:
        delay: float = self.config.base_delay * (2 ** attempt)
        delay = min(delay, self.config.max_delay)
        if self.config.jitter:
            delay = random.uniform(0.0, delay)
        return delay

    async def execute(self, coro: Any) -> Any:
        """Execute a call, retrying on retryable exceptions.

        Args:
            coro: A coroutine function or an awaitable to execute.

        Returns:
            The result of the call.

        Raises:
            The last raised exception once retries are exhausted.
        """
        attempt = 0
        while True:
            try:
                if inspect.isawaitable(coro):
                    return await coro
                return await coro()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                if not self._is_retryable(e):
                    raise
                if attempt >= self.config.max_retries:
                    raise e
                delay = self._calculate_delay(attempt)
                attempt += 1
                await asyncio.sleep(delay)


# ── Resource Tracker ────────────────────────────────────────────────────


class ResourceTracker:
    """Tracks resources and cleanup callbacks for orderly shutdown."""

    def __init__(self) -> None:
        self._resources: list[Any] = []
        self._cleanup_callbacks: list[Any] = []

    def track(self, resource: Any) -> Any:
        """Register a resource to be cleaned up. Returns the resource."""
        self._resources.append(resource)
        return resource

    def on_cleanup(self, callback: Any) -> None:
        """Register a cleanup callback (sync or async)."""
        self._cleanup_callbacks.append(callback)

    async def cleanup(self) -> None:
        """Run all cleanup callbacks and close tracked resources, ignoring errors."""
        for callback in self._cleanup_callbacks:
            try:
                result = callback()
                if inspect.isawaitable(result):
                    await result
            except Exception:
                pass

        for resource in reversed(self._resources):
            try:
                if hasattr(resource, "aclose"):
                    await resource.aclose()
                elif hasattr(resource, "close"):
                    resource.close()
                elif hasattr(resource, "__aexit__"):
                    await resource.__aexit__(None, None, None)
            except Exception:
                pass

        self._resources.clear()
        self._cleanup_callbacks.clear()


# ── Timeouts ────────────────────────────────────────────────────────────


@dataclass
class TimeoutConfig:
    """Timeout settings for session execution."""

    per_call_seconds: float = 30.0
    per_iteration_seconds: float = 120.0
    per_session_seconds: float = 1800.0
    tool_timeout_seconds: float = 30.0


# ── Session Metrics ─────────────────────────────────────────────────────


@dataclass
class SessionMetrics:
    """Per-session operational metrics."""

    session_id: str
    start_time: float = field(default_factory=time.monotonic)
    end_time: float | None = None
    total_iterations: int = 0
    total_tool_calls: int = 0
    total_errors: int = 0
    retry_count: int = 0
    circuit_breaker_opens: int = 0
    total_tokens_used: int = 0
    llm_call_durations: list[float] = field(default_factory=list)
    tool_call_durations: list[float] = field(default_factory=list)
    errors_by_type: dict[str, int] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        end = self.end_time if self.end_time is not None else time.monotonic()
        return max(0.0, end - self.start_time)

    @property
    def avg_llm_call_ms(self) -> float:
        if not self.llm_call_durations:
            return 0.0
        return sum(self.llm_call_durations) / len(self.llm_call_durations) * 1000.0

    @property
    def avg_tool_call_ms(self) -> float:
        if not self.tool_call_durations:
            return 0.0
        return sum(self.tool_call_durations) / len(self.tool_call_durations) * 1000.0

    def record_error(self, error: BaseException) -> None:
        """Record an error by type."""
        self.total_errors += 1
        name = type(error).__name__
        self.errors_by_type[name] = self.errors_by_type.get(name, 0) + 1

    def to_dict(self) -> dict[str, Any]:
        """Export metrics to a serializable dictionary."""
        return {
            "session_id": self.session_id,
            "total_iterations": self.total_iterations,
            "total_tool_calls": self.total_tool_calls,
            "total_errors": self.total_errors,
            "retry_count": self.retry_count,
            "circuit_breaker_opens": self.circuit_breaker_opens,
            "total_tokens_used": self.total_tokens_used,
            "duration_seconds": self.duration_seconds,
        }

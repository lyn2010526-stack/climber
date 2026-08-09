"""Retry, timeout, and error handling policies for node execution."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class RetryPolicy:
    """Exponential backoff retry policy.

    Attributes:
        max_attempts: Maximum number of execution attempts.
        initial_interval: Initial wait before first retry (seconds).
        backoff_factor: Multiplier applied to interval after each retry.
        max_interval: Maximum wait between retries (seconds).
        jitter: Add random jitter to prevent thundering herd.
        retryable_exceptions: Exception types that trigger retry.
    """

    max_attempts: int = 3
    initial_interval: float = 1.0
    backoff_factor: float = 2.0
    max_interval: float = 60.0
    jitter: bool = True
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,)

    def should_retry(self, attempt: int, error: Exception) -> bool:
        """Determine if another retry should be attempted."""
        if attempt >= self.max_attempts:
            return False
        return isinstance(error, self.retryable_exceptions)

    def get_delay(self, attempt: int) -> float:
        """Calculate delay before the next retry."""
        delay = self.initial_interval * (self.backoff_factor ** (attempt - 1))
        delay = min(delay, self.max_interval)
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        return delay


@dataclass
class TimeoutPolicy:
    """Timeout policies for execution control.

    Attributes:
        run_timeout: Maximum total execution time for the entire graph.
        idle_timeout: Maximum time between two super-steps before timeout.
        node_timeout: Default timeout per node execution (None = no limit).
    """

    run_timeout: float | None = None
    idle_timeout: float | None = None
    node_timeout: float | None = None


@runtime_checkable
class ErrorHandler(Protocol):
    """Protocol for custom error handlers."""

    async def handle(self, error: Exception, state: dict[str, Any], node: str) -> dict[str, Any] | None:
        """Handle a node error after retries are exhausted.

        Returns:
            State update dict to continue execution, or None to re-raise.
        """
        ...


class DefaultErrorHandler:
    """Default error handler that logs and optionally continues."""

    def __init__(self, fallback_value: Any = None, continue_on_error: bool = True) -> None:
        self.fallback_value = fallback_value
        self.continue_on_error = continue_on_error

    async def handle(self, error: Exception, state: dict[str, Any], node: str) -> dict[str, Any] | None:
        """Log error and return fallback state update if configured."""
        logger.error(
            "node_error_final",
            node=node,
            error=str(error),
            error_type=type(error).__name__,
        )
        if self.continue_on_error:
            return {"error": str(error), "error_node": node, "__error__": True}
        return None


class CircuitBreaker:
    """Circuit breaker pattern for node failures."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self._failures: dict[str, int] = {}
        self._last_failure: dict[str, float] = {}
        self._state: dict[str, str] = {}  # closed, open, half_open
        self._half_open_calls: dict[str, int] = {}

    @property
    def states(self) -> dict[str, str]:
        return dict(self._state)

    def can_execute(self, node: str) -> bool:
        """Check if a node is allowed to execute."""
        state = self._state.get(node, "closed")
        if state == "closed":
            return True
        if state == "open":
            last_fail = self._last_failure.get(node, 0)
            import time

            if time.monotonic() - last_fail >= self.recovery_timeout:
                self._state[node] = "half_open"
                self._half_open_calls[node] = 0
                return True
            return False
        if state == "half_open":
            return self._half_open_calls.get(node, 0) < self.half_open_max_calls
        return True

    def record_success(self, node: str) -> None:
        """Record a successful execution."""
        self._failures[node] = 0
        self._state[node] = "closed"
        self._half_open_calls.pop(node, None)

    def record_failure(self, node: str) -> None:
        """Record a failed execution."""
        import time

        self._failures[node] = self._failures.get(node, 0) + 1
        self._last_failure[node] = time.monotonic()
        if self._state.get(node) == "half_open":
            self._state[node] = "open"
        elif self._failures[node] >= self.failure_threshold:
            self._state[node] = "open"
            logger.warning("circuit_open", node=node, failures=self._failures[node])


async def execute_with_retry(
    func: Callable[..., Any],
    state: dict[str, Any],
    *,
    retry_policy: RetryPolicy | None = None,
    node_name: str = "",
    **kwargs: Any,
) -> Any:
    """Execute a callable with retry logic.

    Args:
        func: Async or sync callable to execute.
        state: Current state dict passed to func.
        retry_policy: Retry configuration.
        node_name: Name for logging.
        **kwargs: Additional kwargs passed to func.

    Returns:
        The function's return value.

    Raises:
        The last exception if all retries are exhausted.
    """
    retry_policy = retry_policy or RetryPolicy()
    last_error: Exception | None = None

    for attempt in range(1, retry_policy.max_attempts + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(state, **kwargs)
            else:
                result = func(state, **kwargs)
            if attempt > 1:
                logger.info("node_retry_success", node=node_name, attempt=attempt)
            return result
        except Exception as e:
            last_error = e
            if not retry_policy.should_retry(attempt, e):
                logger.error(
                    "node_error_no_retry",
                    node=node_name,
                    attempt=attempt,
                    error=str(e),
                )
                raise
            delay = retry_policy.get_delay(attempt)
            logger.warning(
                "node_retry_scheduled",
                node=node_name,
                attempt=attempt,
                delay=delay,
                error=str(e),
            )
            await asyncio.sleep(delay)

    raise last_error  # type: ignore[misc]

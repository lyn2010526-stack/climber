"""Centralized error handling with API error classification.

Handles:
- 401: Authentication failure (stop immediately)
- 429: Rate limit (exponential backoff)
- 503: Service unavailable (failover to backup)
- Timeout (retry with backoff)
- Connection error (retry with backoff)
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import StrEnum

logger = logging.getLogger(__name__)


class ErrorSeverity(StrEnum):
    RETRY = "retry"           # Can retry with backoff
    FAILOVER = "failover"     # Switch to backup provider
    STOP = "stop"             # Stop immediately (auth failure, quota exceeded)
    WARN = "warn"             # Log warning, continue


@dataclass
class APIError:
    status_code: int | None
    message: str
    severity: ErrorSeverity
    retry_after: float = 0.0

    @classmethod
    def from_status(cls, status: int, message: str = "") -> APIError:
        if status == 401:
            return cls(status, message or "Authentication failed", ErrorSeverity.STOP)
        elif status == 402:
            return cls(status, message or "Quota exhausted", ErrorSeverity.STOP)
        elif status == 429:
            return cls(status, message or "Rate limited", ErrorSeverity.RETRY, retry_after=60.0)
        elif status == 503:
            return cls(status, message or "Service unavailable", ErrorSeverity.FAILOVER)
        elif status >= 500:
            return cls(status, message or "Server error", ErrorSeverity.FAILOVER)
        else:
            return cls(status, message or "Unknown error", ErrorSeverity.RETRY)


@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0


class CircuitBreaker:
    """Circuit breaker pattern for API calls.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests blocked
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failures = 0
        self._last_failure_time: float | None = None
        self._state = "closed"

    @property
    def is_open(self) -> bool:
        if self._state == "open":
            if self._last_failure_time and (time.monotonic() - self._last_failure_time) > self.recovery_timeout:
                self._state = "half_open"
                return False
            return True
        return False

    def record_success(self):
        self._failures = 0
        self._state = "closed"

    def record_failure(self):
        self._failures += 1
        self._last_failure_time = time.monotonic()
        if self._failures >= self.failure_threshold:
            self._state = "open"
            logger.warning("Circuit breaker OPEN after %d failures", self._failures)

    @property
    def state(self) -> str:
        return self._state


class RetryWithBackoff:
    """Execute an async operation with exponential backoff retry."""

    def __init__(self, config: RetryConfig | None = None, circuit_breaker: CircuitBreaker | None = None):
        self.config = config or RetryConfig()
        self.cb = circuit_breaker

    async def execute(self, operation, *args, **kwargs):
        """Execute operation with retry logic."""
        last_error = None
        for attempt in range(self.config.max_retries + 1):
            if self.cb and self.cb.is_open:
                raise Exception("Circuit breaker is OPEN — too many failures, try again later")

            try:
                result = await operation(*args, **kwargs)
                if self.cb:
                    self.cb.record_success()
                return result
            except Exception as e:
                last_error = e
                error = self._classify_error(e)

                if error.severity == ErrorSeverity.STOP:
                    logger.error("Non-retryable error: %s", error.message)
                    raise

                if attempt < self.config.max_retries:
                    delay = min(
                        self.config.base_delay * (self.config.exponential_base ** attempt),
                        self.config.max_delay,
                    )
                    if error.retry_after > 0:
                        delay = max(delay, error.retry_after)
                    logger.warning("Attempt %d failed (%s), retrying in %.1fs", attempt + 1, error.message, delay)
                    await asyncio.sleep(delay)

                if self.cb:
                    self.cb.record_failure()

        raise last_error

    def _classify_error(self, e: Exception) -> APIError:
        """Classify an exception into an APIError."""
        error_str = str(e).lower()

        if "401" in error_str or "unauthorized" in error_str or "authentication" in error_str:
            return APIError(401, str(e), ErrorSeverity.STOP)
        elif "402" in error_str or "quota" in error_str or "insufficient" in error_str:
            return APIError(402, str(e), ErrorSeverity.STOP)
        elif "429" in error_str or "rate limit" in error_str or "too many requests" in error_str:
            return APIError(429, str(e), ErrorSeverity.RETRY, retry_after=60.0)
        elif "503" in error_str or "service unavailable" in error_str:
            return APIError(503, str(e), ErrorSeverity.FAILOVER)
        elif "timeout" in error_str or "timed out" in error_str:
            return APIError(None, str(e), ErrorSeverity.RETRY)
        elif "connection" in error_str:
            return APIError(None, str(e), ErrorSeverity.FAILOVER)
        else:
            return APIError(None, str(e), ErrorSeverity.RETRY)

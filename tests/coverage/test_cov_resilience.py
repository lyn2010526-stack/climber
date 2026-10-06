"""Coverage tests for app.core.resilience.

Covers the circuit breaker state machine, retry handler, resource tracker,
timeout config and session metrics. No real time is spent sleeping: delay
values are driven to zero and ``asyncio.sleep`` is exercised with 0.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import AgentEngineError
from app.core.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
    IterationTimeoutError,
    ResourceTracker,
    RetryConfig,
    RetryHandler,
    SessionMetrics,
    SessionTimeoutError,
    TimeoutConfig,
)

# ── Errors ──────────────────────────────────────────────────────────────


def test_error_classes_inherit_agent_engine_error() -> None:
    assert issubclass(CircuitBreakerOpenError, AgentEngineError)
    assert issubclass(SessionTimeoutError, AgentEngineError)
    assert issubclass(IterationTimeoutError, AgentEngineError)


# ── Circuit breaker ─────────────────────────────────────────────────────


async def test_circuit_breaker_starts_closed_and_passes_calls() -> None:
    cb = CircuitBreaker("svc")
    assert cb.state is CircuitState.CLOSED
    assert cb.is_open is False
    assert cb.failure_count == 0

    async def work() -> str:
        return "ok"

    assert await cb.call(work) == "ok"
    # also accept an already-created awaitable
    assert await cb.call(work()) == "ok"


async def test_circuit_breaker_trips_open_after_threshold() -> None:
    cb = CircuitBreaker("svc", CircuitBreakerConfig(failure_threshold=2, recovery_timeout=60))

    async def boom() -> None:
        raise RuntimeError("nope")

    with pytest.raises(RuntimeError):
        await cb.call(boom)
    assert cb.state is CircuitState.CLOSED
    assert cb.failure_count == 1

    with pytest.raises(RuntimeError):
        await cb.call(boom)
    assert cb.state is CircuitState.OPEN
    assert cb.is_open is True

    with pytest.raises(CircuitBreakerOpenError):
        await cb.call(boom)


async def test_circuit_breaker_recovers_to_half_open() -> None:
    cb = CircuitBreaker("svc", CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.01))
    cb._state = CircuitState.OPEN
    cb._opened_at = 0.0  # force the recovery window to have elapsed
    assert cb.state is CircuitState.HALF_OPEN

    async def ok() -> str:
        return "recovered"

    assert await cb.call(ok) == "recovered"
    assert cb.state is CircuitState.CLOSED
    assert cb.failure_count == 0


async def test_circuit_breaker_half_open_capacity_limit() -> None:
    cb = CircuitBreaker(
        "svc",
        CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.01, half_open_max_calls=1),
    )
    cb._state = CircuitState.HALF_OPEN
    cb._half_open_used = 1

    async def ok() -> str:
        return "x"

    with pytest.raises(CircuitBreakerOpenError):
        await cb.call(ok)


async def test_circuit_breaker_half_open_failure_reopens() -> None:
    cb = CircuitBreaker("svc", CircuitBreakerConfig(failure_threshold=5))
    cb._state = CircuitState.HALF_OPEN

    async def boom() -> None:
        raise ValueError("still broken")

    with pytest.raises(ValueError):
        await cb.call(boom)
    assert cb.state is CircuitState.OPEN


async def test_circuit_breaker_reset() -> None:
    cb = CircuitBreaker("svc", CircuitBreakerConfig(failure_threshold=1))
    cb._state = CircuitState.OPEN
    cb._failure_count = 7
    cb._half_open_used = 3
    cb._opened_at = 123.0
    cb.reset()
    assert cb.state is CircuitState.CLOSED
    assert cb.failure_count == 0
    assert cb._half_open_used == 0
    assert cb._opened_at is None


# ── Retry handler ───────────────────────────────────────────────────────


def test_is_retryable_matrix() -> None:
    handler = RetryHandler(RetryConfig())

    class WithStatus(Exception):
        def __init__(self, status_code: object) -> None:
            super().__init__("http")
            self.status_code = status_code

    assert handler._is_retryable(TimeoutError()) is True
    assert handler._is_retryable(ConnectionError()) is True
    assert handler._is_retryable(OSError()) is True
    assert handler._is_retryable(WithStatus(429)) is True
    assert handler._is_retryable(WithStatus(500)) is True
    assert handler._is_retryable(WithStatus(404)) is False
    assert handler._is_retryable(WithStatus("not-a-number")) is False
    assert handler._is_retryable(ValueError("plain")) is False


def test_calculate_delay_is_capped_and_jittered() -> None:
    no_jitter = RetryHandler(RetryConfig(base_delay=1.0, max_delay=4.0, jitter=False))
    assert no_jitter._calculate_delay(0) == 1.0
    assert no_jitter._calculate_delay(1) == 2.0
    assert no_jitter._calculate_delay(5) == 4.0  # capped at max_delay

    jittered = RetryHandler(RetryConfig(base_delay=1.0, max_delay=4.0, jitter=True))
    for attempt in range(4):
        delay = jittered._calculate_delay(attempt)
        assert 0.0 <= delay <= 4.0


async def test_retry_handler_returns_on_success() -> None:
    handler = RetryHandler(RetryConfig(max_retries=2, base_delay=0, jitter=False))

    async def ok() -> str:
        return "yes"

    assert await handler.execute(ok) == "yes"
    assert await handler.execute(ok()) == "yes"


async def test_retry_handler_retries_then_succeeds() -> None:
    handler = RetryHandler(RetryConfig(max_retries=3, base_delay=0, jitter=False))
    calls = {"n": 0}

    async def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise TimeoutError("slow")
        return "done"

    assert await handler.execute(flaky) == "done"
    assert calls["n"] == 3


async def test_retry_handler_non_retryable_propagates() -> None:
    handler = RetryHandler(RetryConfig(max_retries=3, base_delay=0, jitter=False))

    async def bad() -> None:
        raise ValueError("fatal")

    with pytest.raises(ValueError):
        await handler.execute(bad)


async def test_retry_handler_exhausts_retries() -> None:
    handler = RetryHandler(RetryConfig(max_retries=1, base_delay=0, jitter=False))
    calls = {"n": 0}

    async def always_timeout() -> None:
        calls["n"] += 1
        raise TimeoutError("always")

    with pytest.raises(TimeoutError):
        await handler.execute(always_timeout)
    assert calls["n"] == 2  # initial attempt + 1 retry


async def test_retry_handler_reraises_cancelled() -> None:
    handler = RetryHandler(RetryConfig(max_retries=3, base_delay=0, jitter=False))

    async def cancelled() -> None:
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await handler.execute(cancelled)


# ── Resource tracker ────────────────────────────────────────────────────


async def test_resource_tracker_runs_sync_and_async_cleanups() -> None:
    tracker = ResourceTracker()
    events: list[str] = []

    def sync_cb() -> None:
        events.append("sync")

    async def async_cb() -> None:
        events.append("async")

    def failing_cb() -> None:
        raise RuntimeError("cleanup failed")

    tracker.on_cleanup(sync_cb)
    tracker.on_cleanup(async_cb)
    tracker.on_cleanup(failing_cb)
    await tracker.cleanup()
    assert events == ["sync", "async"]


async def test_resource_tracker_closes_resources_variants() -> None:
    tracker = ResourceTracker()
    closed: list[str] = []

    class AsyncClosable:
        async def aclose(self) -> None:
            closed.append("aclose")

    class SyncClosable:
        def close(self) -> None:
            closed.append("close")

    class AExit:
        async def __aexit__(self, *args: object) -> None:
            closed.append("aexit")

    class Broken:
        async def aclose(self) -> None:
            raise RuntimeError("cannot close")

    tracker.track(AsyncClosable())
    tracker.track(SyncClosable())
    tracker.track(AExit())
    tracker.track(Broken())
    tracker.track(object())  # neither aclose/close/__aexit__
    await tracker.cleanup()
    # resources are cleaned in reverse order
    assert closed == ["aexit", "close", "aclose"]


async def test_resource_tracker_track_returns_resource_and_clears() -> None:
    tracker = ResourceTracker()
    sentinel = object()
    assert tracker.track(sentinel) is sentinel
    await tracker.cleanup()
    assert tracker._resources == []
    assert tracker._cleanup_callbacks == []


# ── Timeouts & metrics ──────────────────────────────────────────────────


def test_timeout_config_defaults() -> None:
    cfg = TimeoutConfig()
    assert cfg.per_call_seconds == 30.0
    assert cfg.per_iteration_seconds == 120.0
    assert cfg.per_session_seconds == 1800.0
    assert cfg.tool_timeout_seconds == 30.0


def test_session_metrics_duration_and_averages() -> None:
    metrics = SessionMetrics(session_id="s1", start_time=100.0)
    assert metrics.duration_seconds >= 0.0
    metrics.end_time = 100.5
    assert metrics.duration_seconds == pytest.approx(0.5)

    assert metrics.avg_llm_call_ms == 0.0
    assert metrics.avg_tool_call_ms == 0.0
    metrics.llm_call_durations = [0.1, 0.3]
    metrics.tool_call_durations = [0.2]
    assert metrics.avg_llm_call_ms == pytest.approx(200.0)
    assert metrics.avg_tool_call_ms == pytest.approx(200.0)


def test_session_metrics_record_error_and_to_dict() -> None:
    metrics = SessionMetrics(session_id="s2")
    metrics.record_error(ValueError("a"))
    metrics.record_error(ValueError("b"))
    metrics.record_error(KeyError("c"))
    assert metrics.total_errors == 3
    assert metrics.errors_by_type == {"ValueError": 2, "KeyError": 1}

    metrics.total_iterations = 4
    metrics.total_tool_calls = 5
    metrics.retry_count = 1
    metrics.circuit_breaker_opens = 2
    metrics.total_tokens_used = 100
    exported = metrics.to_dict()
    assert exported["session_id"] == "s2"
    assert exported["total_iterations"] == 4
    assert exported["total_tool_calls"] == 5
    assert exported["total_errors"] == 3
    assert exported["retry_count"] == 1
    assert exported["circuit_breaker_opens"] == 2
    assert exported["total_tokens_used"] == 100
    assert "duration_seconds" in exported


async def test_retry_handler_uses_asyncio_sleep_with_zero_delay(monkeypatch) -> None:
    """Guards the sleep call path without real waiting."""
    slept: list[float] = []
    real_sleep = asyncio.sleep

    async def fake_sleep(delay: float) -> None:
        slept.append(delay)
        await real_sleep(0)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    handler = RetryHandler(RetryConfig(max_retries=1, base_delay=0, jitter=False))
    calls = {"n": 0}

    async def flaky() -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("down")
        return "up"

    assert await handler.execute(flaky) == "up"
    assert slept == [0.0]


async def test_retry_handler_async_mock_callable() -> None:
    handler = RetryHandler(RetryConfig(max_retries=0))
    mock = AsyncMock(return_value="mocked")
    assert await handler.execute(mock) == "mocked"
    mock.assert_awaited_once()

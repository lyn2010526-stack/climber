"""Coverage tests for app.core.engine.pregel.policies."""

from __future__ import annotations

import pytest

from app.core.engine.pregel.policies import (
    CircuitBreaker,
    DefaultErrorHandler,
    ErrorHandler,
    RetryPolicy,
    TimeoutPolicy,
    execute_with_retry,
)


def test_retry_policy_should_retry() -> None:
    policy = RetryPolicy(max_attempts=3, retryable_exceptions=(ValueError,))
    assert policy.should_retry(1, ValueError("x")) is True
    assert policy.should_retry(3, ValueError("x")) is False
    assert policy.should_retry(1, TypeError("x")) is False


def test_retry_policy_get_delay_no_jitter_and_capped() -> None:
    policy = RetryPolicy(initial_interval=1.0, backoff_factor=2.0, max_interval=5.0, jitter=False)
    assert policy.get_delay(1) == 1.0
    assert policy.get_delay(2) == 2.0
    assert policy.get_delay(3) == 4.0
    assert policy.get_delay(10) == 5.0


def test_retry_policy_get_delay_jitter(monkeypatch) -> None:
    monkeypatch.setattr("app.core.engine.pregel.policies.random.random", lambda: 1.0)
    policy = RetryPolicy(initial_interval=2.0, jitter=True)
    # 0.5 + 1.0*0.5 = 1.0 multiplier
    assert policy.get_delay(1) == 2.0


def test_timeout_policy_defaults() -> None:
    policy = TimeoutPolicy()
    assert policy.run_timeout is None
    assert policy.idle_timeout is None
    assert policy.node_timeout is None


async def test_default_error_handler_continue_and_raise() -> None:
    handler = DefaultErrorHandler()
    assert isinstance(handler, ErrorHandler)
    update = await handler.handle(RuntimeError("boom"), {}, "n")
    assert update is not None
    assert update["error"] == "boom"
    assert update["__error__"] is True

    strict = DefaultErrorHandler(continue_on_error=False)
    assert await strict.handle(RuntimeError("boom"), {}, "n") is None


def test_circuit_breaker_closed_open_recovery() -> None:
    import time

    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=10.0)
    assert cb.states == {}
    assert cb.can_execute("n") is True
    cb.record_failure("n")
    assert cb._state.get("n", "closed") == "closed"
    cb.record_failure("n")
    assert cb._state["n"] == "open"
    assert cb.can_execute("n") is False

    # simulate recovery timeout passing
    cb._last_failure["n"] = time.monotonic() - 100
    assert cb.can_execute("n") is True
    assert cb._state["n"] == "half_open"
    # half_open max calls reached
    cb._half_open_calls["n"] = 1
    assert cb.can_execute("n") is False

    cb.record_success("n")
    assert cb._failures["n"] == 0
    assert cb._state["n"] == "closed"
    assert cb.states == {"n": "closed"}


def test_circuit_breaker_half_open_failure_reopens() -> None:
    cb = CircuitBreaker(failure_threshold=5)
    cb._state["n"] = "half_open"
    cb.record_failure("n")
    assert cb._state["n"] == "open"

    # unknown state value falls through to True
    cb._state["weird"] = "unknown"
    assert cb.can_execute("weird") is True


async def test_execute_with_retry_sync_success() -> None:
    calls = {"n": 0}

    def func(state: dict) -> str:
        calls["n"] += 1
        return "ok"

    assert await execute_with_retry(func, {}) == "ok"
    assert calls["n"] == 1


async def test_execute_with_retry_async_success() -> None:
    async def func(state: dict) -> str:
        return "async-ok"

    assert await execute_with_retry(func, {}) == "async-ok"


async def test_execute_with_retry_then_succeeds() -> None:
    calls = {"n": 0}

    def func(state: dict) -> str:
        calls["n"] += 1
        if calls["n"] < 2:
            raise ValueError("transient")
        return "recovered"

    policy = RetryPolicy(max_attempts=3, initial_interval=0.0, jitter=False)
    assert await execute_with_retry(func, {}, retry_policy=policy) == "recovered"
    assert calls["n"] == 2


async def test_execute_with_retry_non_retryable_raises_immediately() -> None:
    calls = {"n": 0}

    def func(state: dict) -> str:
        calls["n"] += 1
        raise KeyError("fatal")

    policy = RetryPolicy(max_attempts=3, retryable_exceptions=(ValueError,))
    with pytest.raises(KeyError):
        await execute_with_retry(func, {}, retry_policy=policy)
    assert calls["n"] == 1


async def test_execute_with_retry_exhausts_and_raises() -> None:
    def func(state: dict) -> str:
        raise ValueError("always")

    policy = RetryPolicy(max_attempts=2, initial_interval=0.0, jitter=False)
    with pytest.raises(ValueError, match="always"):
        await execute_with_retry(func, {}, retry_policy=policy)


async def test_execute_with_retry_zero_attempts_raises_last_error() -> None:
    def func(state: dict) -> str:  # pragma: no cover - never invoked
        return "nope"

    policy = RetryPolicy(max_attempts=0)
    with pytest.raises(TypeError):
        await execute_with_retry(func, {}, retry_policy=policy)

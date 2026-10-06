"""Coverage tests for app.core.execution.circuit_breaker."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.core.execution.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerRecord,
    CircuitBreakerState,
    TimeoutManager,
)


def test_circuit_breaker_opens_after_threshold() -> None:
    cb = CircuitBreaker(CircuitBreakerConfig(max_failures=2, recovery_timeout=60.0))
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.is_open is False
    assert cb.allow_request() is True
    assert cb.record_failure() is False
    assert cb.record_failure() is True
    assert cb.is_open is True
    assert cb.allow_request() is False
    assert cb.failure_count == 2


def test_circuit_breaker_recovery_to_half_open(monkeypatch) -> None:
    cb = CircuitBreaker(CircuitBreakerConfig(max_failures=1, recovery_timeout=10.0))
    cb.record_failure()
    assert cb.state == CircuitBreakerState.OPEN

    # simulate recovery window elapsed
    monkeypatch.setattr("app.core.execution.circuit_breaker.time.time", lambda: 10_000.0)
    cb._last_failure_time = 0.0
    assert cb._should_try_recovery() is False
    cb._last_failure_time = 1.0
    assert cb._should_try_recovery() is True
    assert cb.state == CircuitBreakerState.HALF_OPEN
    assert cb.allow_request() is True

    cb.record_success()
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.failure_count == 0


def test_circuit_breaker_half_open_failure_reopens() -> None:
    cb = CircuitBreaker(CircuitBreakerConfig(max_failures=5))
    cb._state = CircuitBreakerState.HALF_OPEN
    assert cb.record_failure() is True
    assert cb.state == CircuitBreakerState.OPEN


def test_circuit_breaker_failure_window_prunes(monkeypatch) -> None:
    cb = CircuitBreaker(CircuitBreakerConfig(max_failures=3, failure_window=1.0))
    cb._failure_timestamps = [0.0, 0.0]
    monkeypatch.setattr("app.core.execution.circuit_breaker.time.time", lambda: 5000.0)
    # stale timestamps outside the window are pruned before the threshold check
    assert cb.record_failure() is False
    assert cb.failure_count == 1
    assert cb.state == CircuitBreakerState.CLOSED


def test_circuit_breaker_record_and_reset() -> None:
    cb = CircuitBreaker(name="unit")
    cb.record_success()
    cb.record_failure()
    record = cb.get_record()
    assert isinstance(record, CircuitBreakerRecord)
    assert record.success_count == 1
    assert record.failure_count == 1
    assert record.last_failure_time > 0
    assert record.state in {"closed", "open", "half_open"}

    cb._state = CircuitBreakerState.OPEN
    cb._tripped_at = datetime.now(UTC)
    record2 = cb.get_record()
    assert record2.tripped_at != ""

    cb.reset()
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.failure_count == 0


def test_timeout_manager_lifecycle() -> None:
    tm = TimeoutManager()
    tm.start_task("t1", 100)
    assert tm.check_timeout("t1") is False
    assert tm.get_remaining_time("t1") > 0
    tm.complete_task("t1")
    # completed tasks are no longer "running"
    assert tm.check_timeout("t1") is False
    assert tm.get_remaining_time("t1") == 0.0
    tm.close()


def test_timeout_manager_expired_task() -> None:
    tm = TimeoutManager()
    tm.start_task("t", 100)
    past = (datetime.now(UTC) - timedelta(seconds=10)).isoformat()
    tm._conn.execute("UPDATE task_timeouts SET deadline = ? WHERE task_id = ?", (past, "t"))
    tm._conn.commit()
    assert tm.check_timeout("t") is True
    assert tm.get_timed_out_tasks() == ["t"]
    assert tm.get_remaining_time("t") == 0.0
    tm.fail_task("t")
    assert tm.get_timed_out_tasks() == []
    tm.close()


def test_timeout_manager_unknown_task() -> None:
    tm = TimeoutManager()
    assert tm.check_timeout("missing") is False
    assert tm.get_remaining_time("missing") == 0.0
    tm.close()

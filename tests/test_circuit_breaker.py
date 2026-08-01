"""Tests for the task circuit breaker and loop protection."""

from __future__ import annotations

import pytest

from app.core.task_circuit_breaker import (
    CircuitBreakerAction,
    CircuitBreakerConfig,
    CircuitBreakerReason,
    TaskCircuitBreaker,
)


class TestTaskCircuitBreaker:
    def test_initial_state(self) -> None:
        cb = TaskCircuitBreaker()
        assert not cb.is_tripped
        assert cb.events == []

    def test_normal_execution_no_trip(self) -> None:
        cb = TaskCircuitBreaker()
        for i in range(5):
            event = cb.record_iteration(
                tool_calls=[{"name": "read_file", "arguments": {"path": f"/file{i}.txt"}}],
                progress_delta=0.2,
            )
            assert event is None
        assert not cb.is_tripped

    def test_infinite_loop_detection(self) -> None:
        cb = TaskCircuitBreaker()
        for i in range(3):
            event = cb.record_iteration(
                tool_calls=[{"name": "same_tool", "arguments": {"arg": "same"}}],
                progress_delta=0.0,
            )
            if i == 2:
                assert event is not None
                assert event.reason == CircuitBreakerReason.INFINITE_LOOP
                assert event.action == CircuitBreakerAction.PAUSE
        assert cb.is_tripped

    def test_runaway_task_detection(self) -> None:
        config = CircuitBreakerConfig(max_total_iterations=5)
        cb = TaskCircuitBreaker(config=config)
        event = None
        for i in range(5):
            event = cb.record_iteration(progress_delta=0.01)
        assert event is not None
        assert event.reason == CircuitBreakerReason.RUNAWAY_TASK
        assert event.action == CircuitBreakerAction.ABORT

    def test_stagnant_execution_detection(self) -> None:
        config = CircuitBreakerConfig(
            max_iterations_without_progress=3,
            min_progress_threshold=0.1,
        )
        cb = TaskCircuitBreaker(config=config)
        event = None
        for i in range(4):
            result = cb.record_iteration(progress_delta=0.0)
            if result is not None:
                event = result
        assert event is not None
        assert event.reason == CircuitBreakerReason.STAGNANT_EXECUTION
        assert event.action == CircuitBreakerAction.NOTIFY_CONTINUE

    def test_token_waste_detection(self) -> None:
        config = CircuitBreakerConfig(
            max_token_output_per_iteration=1000,
            min_progress_threshold=0.1,
        )
        cb = TaskCircuitBreaker(config=config)
        event = None
        for i in range(3):
            event = cb.record_iteration(
                token_count=2000,
                progress_delta=0.0,
            )
        assert event is not None
        assert event.reason == CircuitBreakerReason.TOKEN_WASTE

    def test_reset(self) -> None:
        cb = TaskCircuitBreaker()
        for i in range(3):
            cb.record_iteration(
                tool_calls=[{"name": "same", "arguments": {"arg": "same"}}],
                progress_delta=0.0,
            )
        assert cb.is_tripped
        cb.reset()
        assert not cb.is_tripped
        assert cb.events == []
        assert cb._iteration_count == 0

    def test_get_stats(self) -> None:
        cb = TaskCircuitBreaker()
        cb.record_iteration(
            tool_calls=[
                {"name": "tool_a", "arguments": {}},
                {"name": "tool_b", "arguments": {}},
            ],
            progress_delta=0.1,
        )
        stats = cb.get_stats()
        assert stats["iteration_count"] == 1
        assert stats["total_tool_calls"] == 2
        assert stats["unique_tools_used"] == 2
        assert not stats["is_tripped"]

    def test_progress_prevents_stagnation(self) -> None:
        config = CircuitBreakerConfig(
            max_iterations_without_progress=3,
            min_progress_threshold=0.1,
        )
        cb = TaskCircuitBreaker(config=config)
        cb.record_iteration(progress_delta=0.0)
        cb.record_iteration(progress_delta=0.2)
        cb.record_iteration(progress_delta=0.0)
        cb.record_iteration(progress_delta=0.0)
        assert not cb.is_tripped

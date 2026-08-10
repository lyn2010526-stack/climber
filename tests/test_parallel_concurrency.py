"""Tests for parallel/sequential tool execution aggregation."""

from __future__ import annotations

import asyncio

import pytest

from app.core.parallel import ParallelToolExecutor


class _ControlledRegistry:
    """Registry with per-tool delays and failures."""

    def __init__(self):
        self.executed: list[str] = []

    async def execute(self, name: str, arguments: dict) -> str:
        self.executed.append(name)
        if name == "boom":
            raise ValueError("boom!")
        if name == "slow":
            await asyncio.sleep(5)
            return "too-late"
        return f"result-{name}"


def _calls(*names: str) -> list[dict]:
    return [
        {"id": f"call-{name}", "function": {"name": name, "arguments": {}}}
        for name in names
    ]


@pytest.mark.asyncio
async def test_execute_all_runs_in_parallel_and_aggregates():
    registry = _ControlledRegistry()
    executor = ParallelToolExecutor(registry, timeout_per_tool=2.0)

    results = await executor.execute_all(_calls("a", "b", "c"))

    assert len(results) == 3
    assert all(r.success for r in results)
    assert {r.tool_name for r in results} == {"a", "b", "c"}
    assert {r.result for r in results} == {"result-a", "result-b", "result-c"}


@pytest.mark.asyncio
async def test_execute_all_partial_failure_preserves_order():
    registry = _ControlledRegistry()
    executor = ParallelToolExecutor(registry, timeout_per_tool=2.0)

    results = await executor.execute_all(_calls("a", "boom", "c"))

    assert [r.tool_name for r in results] == ["a", "boom", "c"]
    assert [r.success for r in results] == [True, False, True]
    assert "boom!" in results[1].error


@pytest.mark.asyncio
async def test_execute_all_timeout_marks_slow_tool_failed():
    registry = _ControlledRegistry()
    executor = ParallelToolExecutor(registry, timeout_per_tool=0.2)

    results = await executor.execute_all(_calls("a", "slow"))

    assert results[0].success is True
    assert results[1].success is False
    assert results[1].error == "timeout"


@pytest.mark.asyncio
async def test_execute_sequential_preserves_order_and_aggregates_errors():
    registry = _ControlledRegistry()
    executor = ParallelToolExecutor(registry, timeout_per_tool=2.0)

    results = await executor.execute_sequential(_calls("a", "boom", "c"))

    assert [r.tool_name for r in results] == ["a", "boom", "c"]
    assert [r.success for r in results] == [True, False, True]
    assert registry.executed == ["a", "boom", "c"]


@pytest.mark.asyncio
async def test_string_arguments_are_parsed():
    registry = _ControlledRegistry()
    executor = ParallelToolExecutor(registry, timeout_per_tool=2.0)

    calls = [{"id": "c1", "function": {"name": "a", "arguments": '{"x": 1}'}}]
    results = await executor.execute_all(calls)

    assert results[0].success is True


@pytest.mark.asyncio
async def test_malformed_arguments_dont_crash():
    registry = _ControlledRegistry()
    executor = ParallelToolExecutor(registry, timeout_per_tool=2.0)

    calls = [{"id": "c1", "function": {"name": "a", "arguments": "not json {"}}]
    results = await executor.execute_all(calls)

    assert results[0].success is True


@pytest.mark.asyncio
async def test_tool_call_id_is_preserved():
    registry = _ControlledRegistry()
    executor = ParallelToolExecutor(registry, timeout_per_tool=2.0)

    results = await executor.execute_all(_calls("a"))

    assert results[0].tool_call_id == "call-a"


@pytest.mark.asyncio
async def test_validator_blocking_returns_error_for_all():
    registry = _ControlledRegistry()
    executor = ParallelToolExecutor(registry, timeout_per_tool=2.0, validator=lambda name, args: (False, "blocked for test"))

    results = await executor.execute_all(_calls("a", "b"))

    assert all(not r.success for r in results)
    assert all("blocked by sandbox" in r.error for r in results)
    assert registry.executed == []


@pytest.mark.asyncio
async def test_empty_tool_calls_returns_empty():
    registry = _ControlledRegistry()
    executor = ParallelToolExecutor(registry, timeout_per_tool=2.0)

    results = await executor.execute_all([])

    assert results == []

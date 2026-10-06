"""Tests for ParallelToolExecutor validator dispatch (sync and async)."""

from __future__ import annotations

import asyncio
import threading
import time

import pytest

from app.core.parallel import ParallelToolExecutor, Validator
from app.tools import ToolRegistry


def _tool_call(name: str, arguments: dict | None = None, call_id: str = "call-1") -> dict:
    return {
        "id": call_id,
        "function": {"name": name, "arguments": arguments or {}},
    }


def _registry() -> ToolRegistry:
    registry = ToolRegistry()

    async def echo(**kwargs: object) -> str:
        return "tool-ok"

    registry.register("echo", "echo tool", {}, echo)
    return registry


class TestSyncValidatorBackwardCompat:
    """Existing sync validator behavior is unchanged."""

    @pytest.mark.asyncio
    async def test_validator_alias_accepts_sync_callable(self) -> None:
        def v(name: str, args: dict) -> tuple[bool, str]:
            return True, ""

        check: Validator = v
        assert check("echo", {}) == (True, "")

    @pytest.mark.asyncio
    async def test_allowed_validator_runs_tool(self) -> None:
        def validator(name: str, args: dict) -> tuple[bool, str]:
            return True, ""

        executor = ParallelToolExecutor(_registry(), validator=validator)
        results = await executor.execute_all([_tool_call("echo")])
        assert results[0].success is True
        assert results[0].result == "tool-ok"

    @pytest.mark.asyncio
    async def test_blocked_validator_returns_sandbox_error(self) -> None:
        def validator(name: str, args: dict) -> tuple[bool, str]:
            return False, "denied"

        executor = ParallelToolExecutor(_registry(), validator=validator)
        results = await executor.execute_all([_tool_call("echo")])
        assert results[0].success is False
        assert results[0].error == "blocked by sandbox: denied"

    @pytest.mark.asyncio
    async def test_validator_exception_reported(self) -> None:
        def bad(name: str, args: dict) -> tuple[bool, str]:
            raise RuntimeError("boom")

        executor = ParallelToolExecutor(_registry(), validator=bad)
        results = await executor.execute_all([_tool_call("echo")])
        assert results[0].success is False
        assert results[0].error == "validator error: boom"

    @pytest.mark.asyncio
    async def test_sync_validator_receives_name_and_arguments(self) -> None:
        seen: list[tuple[str, dict]] = []

        def validator(name: str, args: dict) -> tuple[bool, str]:
            seen.append((name, args))
            return True, ""

        executor = ParallelToolExecutor(_registry(), validator=validator)
        await executor.execute_all([_tool_call("echo", {"path": "data/report.csv"})])
        assert seen == [("echo", {"path": "data/report.csv"})]


class TestAsyncValidator:
    """Async validators are awaited correctly."""

    @pytest.mark.asyncio
    async def test_async_validator_allow_is_awaited(self) -> None:
        seen: list[tuple[str, dict]] = []

        async def validator(name: str, args: dict) -> tuple[bool, str]:
            seen.append((name, args))
            return True, ""

        executor = ParallelToolExecutor(_registry(), validator=validator)
        results = await executor.execute_all([_tool_call("echo", {"x": 1})])
        assert results[0].success is True
        assert results[0].result == "tool-ok"
        assert seen == [("echo", {"x": 1})]

    @pytest.mark.asyncio
    async def test_async_validator_deny_is_awaited(self) -> None:
        async def validator(name: str, args: dict) -> tuple[bool, str]:
            return False, "async-denied"

        executor = ParallelToolExecutor(_registry(), validator=validator)
        results = await executor.execute_all([_tool_call("echo")])
        assert results[0].success is False
        assert results[0].error == "blocked by sandbox: async-denied"

    @pytest.mark.asyncio
    async def test_async_validator_exception_reported(self) -> None:
        async def validator(name: str, args: dict) -> tuple[bool, str]:
            raise RuntimeError("async boom")

        executor = ParallelToolExecutor(_registry(), validator=validator)
        results = await executor.execute_all([_tool_call("echo")])
        assert results[0].success is False
        assert results[0].error == "validator error: async boom"

    @pytest.mark.asyncio
    async def test_async_validator_with_sequential_execution(self) -> None:
        async def validator(name: str, args: dict) -> tuple[bool, str]:
            return True, ""

        executor = ParallelToolExecutor(_registry(), validator=validator)
        results = await executor.execute_sequential([_tool_call("echo"), _tool_call("echo")])
        assert [r.result for r in results] == ["tool-ok", "tool-ok"]


class TestSyncValidatorOffEventLoop:
    """Sync validators run in a worker thread and never block the event loop."""

    @pytest.mark.asyncio
    async def test_sync_validator_runs_off_main_thread(self) -> None:
        seen: list[bool] = []

        def validator(name: str, args: dict) -> tuple[bool, str]:
            seen.append(threading.current_thread() is threading.main_thread())
            return True, ""

        executor = ParallelToolExecutor(_registry(), validator=validator)
        await executor.execute_all([_tool_call("echo")])
        assert seen == [False]

    @pytest.mark.asyncio
    async def test_slow_sync_validators_concurrent_not_serial(self) -> None:
        delay = 0.25

        def slow_validator(name: str, args: dict) -> tuple[bool, str]:
            time.sleep(delay)
            return True, ""

        executor = ParallelToolExecutor(_registry(), validator=slow_validator)
        start = time.monotonic()
        results = await executor.execute_all(
            [
                _tool_call("echo", call_id="a"),
                _tool_call("echo", call_id="b"),
            ]
        )
        elapsed = time.monotonic() - start

        assert all(r.success for r in results)
        assert elapsed < 2 * delay, f"validators appear serial: {elapsed:.3f}s"


class TestMixedRegistrations:
    """Sync and async validators both work through the same executor path."""

    @pytest.mark.asyncio
    async def test_sync_and_async_validators_both_work(self) -> None:
        registry = _registry()

        def sync_validator(name: str, args: dict) -> tuple[bool, str]:
            return name != "blocked-sync", "sync deny"

        async def async_validator(name: str, args: dict) -> tuple[bool, str]:
            return name != "blocked-async", "async deny"

        sync_exec = ParallelToolExecutor(registry, validator=sync_validator)
        async_exec = ParallelToolExecutor(registry, validator=async_validator)
        sync_results, async_results = await asyncio.gather(
            sync_exec.execute_all(
                [
                    _tool_call("echo", call_id="s-allow"),
                    _tool_call("blocked-sync", call_id="s-deny"),
                ]
            ),
            async_exec.execute_all(
                [
                    _tool_call("echo", call_id="a-allow"),
                    _tool_call("blocked-async", call_id="a-deny"),
                ]
            ),
        )

        assert sync_results[0].success is True
        assert sync_results[0].result == "tool-ok"
        assert sync_results[1].success is False
        assert sync_results[1].error == "blocked by sandbox: sync deny"
        assert async_results[0].success is True
        assert async_results[0].result == "tool-ok"
        assert async_results[1].success is False
        assert async_results[1].error == "blocked by sandbox: async deny"

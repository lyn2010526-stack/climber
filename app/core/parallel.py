"""Parallel and sequential tool execution."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.tools import ToolRegistry


@dataclass
class ToolExecutionResult:
    tool_name: str
    result: str = ""
    error: str = ""
    success: bool = True
    duration_ms: float = 0.0
    arguments: dict[str, Any] | None = None
    tool_call_id: str = ""


# Validator callback: (tool_name, arguments) -> (allowed, reason)
Validator = Callable[[str, dict[str, Any]], tuple[bool, str]]


class ParallelToolExecutor:
    """Execute multiple tool calls in parallel or sequential."""

    def __init__(self, registry: ToolRegistry, timeout_per_tool: float = 30.0, validator: Validator | None = None, session: Any = None):
        self._registry = registry
        self._timeout = timeout_per_tool
        self._validator = validator
        self._session = session

    async def execute_all(self, tool_calls: list[dict[str, Any]]) -> list[ToolExecutionResult]:
        tasks = []
        for tc in tool_calls:
            name, args, parse_error, tool_call_id = self._parse_tool_call(tc)
            if parse_error:
                tasks.append(self._failed_result_async(name, parse_error, tool_call_id))
                continue
            tasks.append(self._execute_one(name, args, tool_call_id))
        return await asyncio.gather(*tasks)

    async def execute_sequential(self, tool_calls: list[dict[str, Any]]) -> list[ToolExecutionResult]:
        results = []
        for tc in tool_calls:
            name, args, parse_error, tool_call_id = self._parse_tool_call(tc)
            if parse_error:
                results.append(self._failed_result(name, parse_error, tool_call_id))
                continue
            results.append(await self._execute_one(name, args, tool_call_id))
        return results

    @staticmethod
    def _parse_tool_call(tc: dict[str, Any]) -> tuple[str, dict[str, Any], str, str]:
        function = tc.get("function", {})
        name = function.get("name", "") if isinstance(function, dict) else ""
        args = function.get("arguments", {}) if isinstance(function, dict) else {}
        tool_call_id = tc.get("id", "")
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError as exc:
                return name, {}, f"invalid tool arguments: {exc.msg}", tool_call_id
        if not isinstance(args, dict):
            return name, {}, "invalid tool arguments: expected an object", tool_call_id
        return name, args, "", tool_call_id

    @staticmethod
    def _failed_result(name: str, error: str, tool_call_id: str) -> ToolExecutionResult:
        return ToolExecutionResult(
            tool_name=name,
            error=error,
            success=False,
            arguments={},
            tool_call_id=tool_call_id,
        )

    @staticmethod
    async def _failed_result_async(name: str, error: str, tool_call_id: str) -> ToolExecutionResult:
        return ParallelToolExecutor._failed_result(name, error, tool_call_id)

    async def _execute_one(self, name: str, arguments: dict[str, Any], tool_call_id: str = "") -> ToolExecutionResult:
        start = asyncio.get_event_loop().time()
        # Pre-execution safety check
        if self._validator is not None:
            try:
                allowed, reason = self._validator(name, arguments)
            except Exception as e:
                duration = (asyncio.get_event_loop().time() - start) * 1000
                return ToolExecutionResult(
                    tool_name=name,
                    error=f"validator error: {e}",
                    success=False,
                    duration_ms=duration,
                    arguments=arguments,
                    tool_call_id=tool_call_id,
                )
            if not allowed:
                duration = (asyncio.get_event_loop().time() - start) * 1000
                return ToolExecutionResult(
                    tool_name=name,
                    error=f"blocked by sandbox: {reason}",
                    success=False,
                    duration_ms=duration,
                    arguments=arguments,
                    tool_call_id=tool_call_id,
                )
        try:
            result = await asyncio.wait_for(
                self._registry.execute_result(name, arguments),
                timeout=self._timeout,
            )
            duration = (asyncio.get_event_loop().time() - start) * 1000
            return ToolExecutionResult(tool_name=name, result=result.result, error=result.error,
                                       success=result.success, duration_ms=duration,
                                       arguments=arguments, tool_call_id=tool_call_id)
        except TimeoutError:
            duration = (asyncio.get_event_loop().time() - start) * 1000
            return ToolExecutionResult(tool_name=name, error="timeout", success=False, duration_ms=duration, arguments=arguments, tool_call_id=tool_call_id)
        except asyncio.CancelledError:
            duration = (asyncio.get_event_loop().time() - start) * 1000
            return ToolExecutionResult(tool_name=name, error="cancelled", success=False, duration_ms=duration, arguments=arguments, tool_call_id=tool_call_id)
        except Exception as e:
            duration = (asyncio.get_event_loop().time() - start) * 1000
            return ToolExecutionResult(tool_name=name, error=str(e), success=False, duration_ms=duration, arguments=arguments, tool_call_id=tool_call_id)

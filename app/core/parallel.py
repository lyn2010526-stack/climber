"""Parallel and sequential tool execution."""

from __future__ import annotations

import asyncio
import inspect
import json
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
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

    def observation(self) -> dict[str, Any]:
        """Expose only execution facts; no inferred tool semantics."""
        return {
            "tool": self.tool_name,
            "arguments": dict(self.arguments or {}),
            "result": self.result,
            "error": self.error,
            "success": self.success,
            "duration_ms": self.duration_ms,
        }


# Validator callback: (tool_name, arguments) -> (allowed, reason)
# `Validator` remains the sync alias so existing registrars are unaffected;
# executors may also be given an async callable via `ValidatorLike`.
SyncValidator = Callable[[str, dict[str, Any]], tuple[bool, str]]
AsyncValidator = Callable[[str, dict[str, Any]], Coroutine[Any, Any, tuple[bool, str]]]
Validator = SyncValidator
ValidatorLike = SyncValidator | AsyncValidator


class ParallelToolExecutor:
    """Execute multiple tool calls in parallel or sequential."""

    def __init__(
        self,
        registry: ToolRegistry,
        timeout_per_tool: float = 30.0,
        validator: ValidatorLike | None = None,
        session: Any = None,
    ):
        self._registry = registry
        self._timeout = timeout_per_tool
        self._validator = validator
        self._session = session

    async def execute_all(self, tool_calls: list[dict[str, Any]]) -> list[ToolExecutionResult]:
        tasks = []
        for tc in tool_calls:
            name = tc.get("function", {}).get("name", "")
            args = tc.get("function", {}).get("arguments", {})
            tool_call_id = tc.get("id", "")
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            elif not isinstance(args, dict):
                args = {}
            tasks.append(self._execute_one(name, args, tool_call_id))
        return await asyncio.gather(*tasks)

    async def execute_sequential(
        self, tool_calls: list[dict[str, Any]]
    ) -> list[ToolExecutionResult]:
        results = []
        for tc in tool_calls:
            name = tc.get("function", {}).get("name", "")
            args = tc.get("function", {}).get("arguments", {})
            tool_call_id = tc.get("id", "")
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            elif not isinstance(args, dict):
                args = {}
            results.append(await self._execute_one(name, args, tool_call_id))
        return results

    async def _execute_one(
        self, name: str, arguments: dict[str, Any], tool_call_id: str = ""
    ) -> ToolExecutionResult:
        start = asyncio.get_event_loop().time()
        # Pre-execution safety check
        if self._validator is not None:
            try:
                if inspect.iscoroutinefunction(self._validator):
                    allowed, reason = await self._validator(name, arguments)
                else:
                    # Sync validators (e.g. guardrails-ai Validator.validate) must not
                    # block the event loop, so they run in the default thread pool.
                    allowed, reason = await asyncio.to_thread(self._validator, name, arguments)
            except Exception as e:
                return ToolExecutionResult(
                    tool_name=name,
                    error=f"validator error: {e}",
                    success=False,
                    duration_ms=0,
                    tool_call_id=tool_call_id,
                )
            if not allowed:
                duration = (asyncio.get_event_loop().time() - start) * 1000
                return ToolExecutionResult(
                    tool_name=name,
                    error=f"blocked by sandbox: {reason}",
                    success=False,
                    duration_ms=duration,
                    tool_call_id=tool_call_id,
                )
        try:
            result = await asyncio.wait_for(
                self._registry.execute(name, arguments),
                timeout=self._timeout,
            )
            duration = (asyncio.get_event_loop().time() - start) * 1000
            if self._is_error_result(result):
                return ToolExecutionResult(
                    tool_name=name,
                    result=str(result),
                    error=str(result),
                    success=False,
                    duration_ms=duration,
                    arguments=arguments,
                    tool_call_id=tool_call_id,
                )
            return ToolExecutionResult(
                tool_name=name,
                result=result,
                duration_ms=duration,
                arguments=arguments,
                tool_call_id=tool_call_id,
            )
        except TimeoutError:
            return ToolExecutionResult(
                tool_name=name,
                error="timeout",
                success=False,
                arguments=arguments,
                tool_call_id=tool_call_id,
            )
        except asyncio.CancelledError:
            # Cancellation must propagate; swallowing it would keep the parent
            # task alive and report a cancelled tool as an ordinary failure.
            raise
        except Exception as e:
            return ToolExecutionResult(
                tool_name=name,
                error=str(e),
                success=False,
                arguments=arguments,
                tool_call_id=tool_call_id,
            )

    @staticmethod
    def _is_error_result(result: Any) -> bool:
        """Detect failure results beyond the known "Error executing" prefix.

        Registry-level exceptions are formatted with the "Error executing"
        prefix, but tools may also return structured errors (JSON with an
        error message, success:false, or isError:true). Those shapes must be
        reported as failures so the model receives the real failure reason.
        """
        if isinstance(result, str):
            if result.startswith("Error executing "):
                return True
            try:
                parsed = json.loads(result)
            except (json.JSONDecodeError, ValueError, TypeError):
                return False
        else:
            parsed = result
        if isinstance(parsed, dict):
            if isinstance(parsed.get("error"), str) and parsed.get("error"):
                return True
            if parsed.get("success") is False:
                return True
            if parsed.get("isError") is True:
                return True
        return False

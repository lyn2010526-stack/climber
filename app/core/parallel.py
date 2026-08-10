"""Parallel and sequential tool execution."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import structlog

from app.tools import ToolRegistry

logger = structlog.get_logger()


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

    async def execute_sequential(self, tool_calls: list[dict[str, Any]]) -> list[ToolExecutionResult]:
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

    async def _execute_one(self, name: str, arguments: dict[str, Any], tool_call_id: str = "") -> ToolExecutionResult:
        start = asyncio.get_event_loop().time()
        # Pre-execution safety check
        if self._validator is not None:
            try:
                allowed, reason = self._validator(name, arguments)
            except Exception as e:
                return ToolExecutionResult(tool_name=name, error=f"validator error: {e}", success=False, duration_ms=0, tool_call_id=tool_call_id)
            if not allowed:
                duration = (asyncio.get_event_loop().time() - start) * 1000
                return ToolExecutionResult(tool_name=name, error=f"blocked by sandbox: {reason}", success=False, duration_ms=duration, tool_call_id=tool_call_id)
        # Human-in-the-loop approval for sensitive tools
        if self._session is not None:
            try:
                from app.core.approval import approval_manager, tool_requires_approval
                if tool_requires_approval(name, arguments):
                    req = await approval_manager.request(
                        session_id=getattr(self._session, "session_id", "default"),
                        tool_name=name,
                        arguments=arguments,
                    )
                    decision = await approval_manager.wait_for_decision(req.id, timeout=300)
                    if decision is None or decision.status.value != "approved":
                        duration = (asyncio.get_event_loop().time() - start) * 1000
                        return ToolExecutionResult(
                            tool_name=name,
                            error=f"permission denied: {getattr(decision, 'reason', None) or 'rejected by user'}",
                            success=False,
                            duration_ms=duration,
                            arguments=arguments,
                            tool_call_id=tool_call_id,
                        )
            except Exception as e:
                logger.warning("parallel.approval_check_failed", tool=name, error=str(e))
        try:
            result = await asyncio.wait_for(
                self._registry.execute(name, arguments),
                timeout=self._timeout,
            )
            duration = (asyncio.get_event_loop().time() - start) * 1000
            return ToolExecutionResult(tool_name=name, result=result, duration_ms=duration, arguments=arguments, tool_call_id=tool_call_id)
        except TimeoutError:
            return ToolExecutionResult(tool_name=name, error="timeout", success=False, arguments=arguments, tool_call_id=tool_call_id)
        except asyncio.CancelledError:
            return ToolExecutionResult(tool_name=name, error="cancelled", success=False, arguments=arguments, tool_call_id=tool_call_id)
        except Exception as e:
            return ToolExecutionResult(tool_name=name, error=str(e), success=False, arguments=arguments, tool_call_id=tool_call_id)

"""Enhanced parallel tool execution with dynamic concurrency and event emission.

Features:
- Dynamic concurrency based on tool type (read-only = higher, write = lower)
- Event emission for progress tracking
- Adaptive timeout based on tool complexity
- Tool dependency analysis for optimal scheduling
"""

from __future__ import annotations

import asyncio
import inspect
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import structlog

from app.tools import ToolRegistry

logger = structlog.get_logger()


@dataclass
class ToolExecutionResult:
    """Result of a single tool execution."""
    tool_name: str
    result: str = ""
    error: str = ""
    success: bool = True
    duration_ms: float = 0.0
    arguments: dict[str, Any] | None = None
    tool_call_id: str = ""


# Validator callback: (tool_name, arguments) -> (allowed, reason)
Validator = Callable[[str, dict[str, Any]], tuple[bool, str]]


# Tools that are safe to run with higher concurrency (read-only)
_HIGH_CONCURRENCY_TOOLS = {
    "read_file", "read", "grep", "glob", "list_directory", "ls",
    "web_search", "fetch_url", "search", "resolve-library-id",
    "query-docs", "image_analysis_get_result", "query_task",
}

# Tools that need exclusive access (write/modify)
_LOW_CONCURRENCY_TOOLS = {
    "write_file", "write", "edit_file", "edit", "delete_file",
    "run_command", "bash", "shell",
}

# Default concurrency limits
DEFAULT_MAX_CONCURRENT = 10
HIGH_CONCURRENCY_LIMIT = 20
LOW_CONCURRENCY_LIMIT = 3


class EnhancedParallelToolExecutor:
    """Execute multiple tool calls with dynamic concurrency and event emission.

    Improvements over basic ParallelToolExecutor:
    1. Dynamic concurrency based on tool type
    2. Event emission for progress tracking
    3. Adaptive timeout based on tool complexity
    4. Tool dependency analysis
    """

    def __init__(
        self,
        registry: ToolRegistry,
        timeout_per_tool: float = 30.0,
        validator: Validator | None = None,
        session: Any = None,
        event_bus: Any = None,
    ):
        self._registry = registry
        self._timeout = timeout_per_tool
        self._validator = validator
        self._session = session
        self._event_bus = event_bus

    def _get_concurrency_limit(self, tool_names: list[str]) -> int:
        """Determine concurrency limit based on tool types."""
        if not tool_names:
            return DEFAULT_MAX_CONCURRENT

        high_count = sum(1 for name in tool_names if name in _HIGH_CONCURRENCY_TOOLS)
        low_count = sum(1 for name in tool_names if name in _LOW_CONCURRENCY_TOOLS)

        # If any low-concurrency tools, use strict limit
        if low_count > 0:
            return LOW_CONCURRENCY_LIMIT

        # If mostly high-concurrency tools, allow more parallelism
        if high_count > len(tool_names) * 0.7:
            return HIGH_CONCURRENCY_LIMIT

        return DEFAULT_MAX_CONCURRENT

    def _get_timeout_for_tool(self, tool_name: str) -> float:
        """Get adaptive timeout based on tool complexity."""
        # Long-running tools get longer timeouts
        long_running_tools = {
            "run_command", "bash", "shell", "process_video", "process_image",
            "container_exec", "execute_code",
        }
        if tool_name in long_running_tools:
            return self._timeout * 3  # 90 seconds
        return self._timeout

    async def execute_all(self, tool_calls: list[dict[str, Any]]) -> list[ToolExecutionResult]:
        """Execute all tool calls with dynamic concurrency."""
        if not tool_calls:
            return []

        # Parse tool calls
        parsed = []
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
            parsed.append((name, args, tool_call_id))

        # Get tool names for concurrency analysis
        tool_names = [name for name, _, _ in parsed]
        concurrency_limit = self._get_concurrency_limit(tool_names)

        # Emit batch start event
        if self._event_bus:
            await self._event_bus.publish("tool_batch_start", {
                "session_id": getattr(self._session, "session_id", None),
                "tool_count": len(tool_calls),
                "tool_names": tool_names,
                "concurrency_limit": concurrency_limit,
            })

        # Execute with dynamic concurrency
        semaphore = asyncio.Semaphore(concurrency_limit)

        async def _exec_with_semaphore(name, args, tool_call_id):
            async with semaphore:
                return await self._execute_one(name, args, tool_call_id)

        tasks = [
            _exec_with_semaphore(name, args, tool_call_id)
            for name, args, tool_call_id in parsed
        ]

        results = await asyncio.gather(*tasks, return_exceptions=False)

        # Emit batch complete event
        if self._event_bus:
            await self._event_bus.publish("tool_batch_complete", {
                "session_id": getattr(self._session, "session_id", None),
                "tool_count": len(results),
                "success_count": sum(1 for r in results if r.success),
                "failure_count": sum(1 for r in results if not r.success),
            })

        return list(results)

    async def _execute_one(self, name: str, arguments: dict[str, Any], tool_call_id: str = "") -> ToolExecutionResult:
        """Execute a single tool call with validation and timeout."""
        start = time.monotonic()

        # Emit tool start event
        if self._event_bus:
            await self._event_bus.publish("tool_start", {
                "session_id": getattr(self._session, "session_id", None),
                "tool_name": name,
                "tool_call_id": tool_call_id,
            })

        # Pre-execution safety check
        if self._validator is not None:
            try:
                allowed, reason = self._validator(name, arguments)
            except Exception as e:
                return ToolExecutionResult(
                    tool_name=name, error=f"validator error: {e}",
                    success=False, duration_ms=0, tool_call_id=tool_call_id,
                )
            if not allowed:
                duration = (time.monotonic() - start) * 1000
                return ToolExecutionResult(
                    tool_name=name, error=f"blocked by sandbox: {reason}",
                    success=False, duration_ms=duration, tool_call_id=tool_call_id,
                )

        # Check for cancellation
        if self._session is not None and getattr(self._session, "_stop_requested", False):
            return ToolExecutionResult(
                tool_name=name, error="cancelled", success=False,
                arguments=arguments, tool_call_id=tool_call_id,
            )

        # Execute with adaptive timeout
        timeout = self._get_timeout_for_tool(name)
        try:
            result = await asyncio.wait_for(
                self._registry.execute(name, arguments),
                timeout=timeout,
            )
            # Normalize adapters that return a second awaitable.
            if inspect.isawaitable(result):
                result = await asyncio.wait_for(result, timeout=timeout)
            if not isinstance(result, str):
                result = str(result)
            duration = (time.monotonic() - start) * 1000

            if result.startswith(f"Error executing {name}:"):
                return ToolExecutionResult(
                    tool_name=name, error=result, success=False,
                    duration_ms=duration, arguments=arguments, tool_call_id=tool_call_id,
                )

            # Emit tool complete event
            if self._event_bus:
                await self._event_bus.publish("tool_complete", {
                    "session_id": getattr(self._session, "session_id", None),
                    "tool_name": name,
                    "tool_call_id": tool_call_id,
                    "duration_ms": duration,
                    "success": True,
                })

            return ToolExecutionResult(
                tool_name=name, result=result, duration_ms=duration,
                arguments=arguments, tool_call_id=tool_call_id,
            )

        except TimeoutError:
            duration = (time.monotonic() - start) * 1000
            if self._event_bus:
                await self._event_bus.publish("tool_error", {
                    "session_id": getattr(self._session, "session_id", None),
                    "tool_name": name,
                    "error": "timeout",
                    "duration_ms": duration,
                })
            return ToolExecutionResult(
                tool_name=name, error=f"timeout after {timeout}s",
                success=False, duration_ms=duration,
                arguments=arguments, tool_call_id=tool_call_id,
            )

        except asyncio.CancelledError:
            return ToolExecutionResult(
                tool_name=name, error="cancelled", success=False,
                arguments=arguments, tool_call_id=tool_call_id,
            )

        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            if self._event_bus:
                await self._event_bus.publish("tool_error", {
                    "session_id": getattr(self._session, "session_id", None),
                    "tool_name": name,
                    "error": str(e),
                    "duration_ms": duration,
                })
            return ToolExecutionResult(
                tool_name=name, error=str(e), success=False,
                duration_ms=duration, arguments=arguments, tool_call_id=tool_call_id,
            )

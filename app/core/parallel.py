"""Parallel and sequential tool execution."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.tools import ToolRegistry

# Default cap on a single tool result handed back to the model. Anthropic caps
# Claude Code tool responses at 25,000 tokens and reports a single Slack tool
# costing 206 tokens detailed vs 72 concise, so unbounded output is the
# dominant avoidable consumer of an agent's context. Measured in characters
# rather than tokens because the executor has no tokenizer, and the
# chars/token ratio is stable enough for a guardrail (3-4 chars per token).
DEFAULT_MAX_RESULT_CHARS = 60_000
DEFAULT_MAX_CONCURRENCY = 8


def _parse_max_concurrency(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return DEFAULT_MAX_CONCURRENCY
    return parsed if parsed > 0 else DEFAULT_MAX_CONCURRENCY


def truncate_tool_result(result: Any, max_chars: int | None) -> Any:
    """Cap a tool result, appending a notice that tells the model how to recover.

    Truncating silently would lose content the model cannot know it missed.
    The notice names the original size and the cheaper access patterns, which
    is the steering Anthropic pairs with truncation.

    Args:
        result: Whatever the tool returned; non-strings pass through untouched.
        max_chars: Character budget, or None to disable the cap.

    Returns:
        The result unchanged, or a truncated string ending in a notice.
    """
    if max_chars is None or not isinstance(result, str) or len(result) <= max_chars:
        return result
    head = max_chars
    notice = (
        f"\n\n[truncated: {len(result)} characters total, showing the first {head}. "
        "To get the rest, narrow the request -- request a specific range, filter or "
        "paginate, or ask for a summary of the region you need instead of the whole "
        "result.]"
    )
    return result[:head] + notice


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

    def __init__(
        self,
        registry: ToolRegistry,
        timeout_per_tool: float = 30.0,
        validator: Validator | None = None,
        session: Any = None,
        max_result_chars: int | None = DEFAULT_MAX_RESULT_CHARS,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
    ):
        self._registry = registry
        self._timeout = timeout_per_tool
        self._validator = validator
        self._session = session
        self.max_result_chars = max_result_chars
        self.max_concurrency = _parse_max_concurrency(max_concurrency)

    async def execute_all(self, tool_calls: list[dict[str, Any]]) -> list[ToolExecutionResult]:
        semaphore = asyncio.Semaphore(self.max_concurrency)
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
            tasks.append(self._execute_bounded(semaphore, name, args, tool_call_id))
        return await asyncio.gather(*tasks)

    async def _execute_bounded(
        self,
        semaphore: asyncio.Semaphore,
        name: str,
        arguments: dict[str, Any],
        tool_call_id: str,
    ) -> ToolExecutionResult:
        async with semaphore:
            return await self._execute_one(name, arguments, tool_call_id)

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
        try:
            result = await asyncio.wait_for(
                self._registry.execute(name, arguments),
                timeout=self._timeout,
            )
            duration = (asyncio.get_event_loop().time() - start) * 1000
            return ToolExecutionResult(
                tool_name=name,
                result=truncate_tool_result(result, self.max_result_chars),
                duration_ms=duration,
                arguments=arguments,
                tool_call_id=tool_call_id,
            )
        except TimeoutError:
            return ToolExecutionResult(tool_name=name, error="timeout", success=False, arguments=arguments, tool_call_id=tool_call_id)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            return ToolExecutionResult(tool_name=name, error=str(e), success=False, arguments=arguments, tool_call_id=tool_call_id)

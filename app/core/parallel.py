"""Parallel and sequential tool execution."""

from __future__ import annotations

import asyncio
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
        return await self._gather_semaphore(*tasks)

    async def _gather_semaphore(self, *tasks: asyncio.Task) -> list[ToolExecutionResult]:
        semaphore = asyncio.Semaphore(10)

        async def _sem(task):
            async with semaphore:
                return await task

        return await asyncio.gather(*[_sem(t) for t in tasks])

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

    async def _increment_pending_approval(self) -> int:
        """Increment the session-wide pending approval count atomically, return the new value."""
        session = self._session
        lock = getattr(session, "_approval_count_lock", None)
        if lock is None:
            lock = asyncio.Lock()
            session._approval_count_lock = lock
        async with lock:
            count = getattr(session, "_pending_approval_count", 0) + 1
            session._pending_approval_count = count
            return count

    async def _decrement_pending_approval(self) -> int:
        """Decrement the session-wide pending approval count atomically, return the new value."""
        session = self._session
        lock = getattr(session, "_approval_count_lock", None)
        if lock is None:
            lock = asyncio.Lock()
            session._approval_count_lock = lock
        async with lock:
            count = max(0, getattr(session, "_pending_approval_count", 1) - 1)
            session._pending_approval_count = count
            return count

    async def _execute_one(self, name: str, arguments: dict[str, Any], tool_call_id: str = "") -> ToolExecutionResult:
        start = time.monotonic()
        validator_requires_approval = False
        # Pre-execution safety check
        if self._validator is not None:
            try:
                allowed, reason = self._validator(name, arguments)
            except Exception as e:
                return ToolExecutionResult(tool_name=name, error=f"validator error: {e}", success=False, duration_ms=0, tool_call_id=tool_call_id)
            if not allowed:
                duration = (time.monotonic() - start) * 1000
                return ToolExecutionResult(tool_name=name, error=f"blocked by sandbox: {reason}", success=False, duration_ms=duration, tool_call_id=tool_call_id)
            validator_requires_approval = reason.startswith("Approval required")
        # Human-in-the-loop approval for sensitive tools
        if self._session is not None:
            try:
                from app.core.approval import approval_manager, tool_requires_approval
                from app.core.permission_rules import RuleDecision
                permission_decision = None
                session_config = getattr(self._session, "permission_config", None)
                if session_config is not None:
                    permission_decision = session_config.evaluate(name, arguments)
                if permission_decision == RuleDecision.DENY:
                    duration = (time.monotonic() - start) * 1000
                    return ToolExecutionResult(
                        tool_name=name,
                        error=f"permission denied: {name}",
                        success=False,
                        duration_ms=duration,
                        arguments=arguments,
                        tool_call_id=tool_call_id,
                    )
                requires_approval = validator_requires_approval or permission_decision == RuleDecision.ASK or (
                    tool_requires_approval(name, arguments)
                    and permission_decision != RuleDecision.ALLOW
                )
                if requires_approval:
                    req = await approval_manager.request(
                        user_id=getattr(self._session, "user_id", "default-user"),
                        session_id=getattr(self._session, "session_id", "default"),
                        tool_name=name,
                        arguments=arguments,
                    )
                    state_machine = getattr(self._session, "state_machine", None)
                    await self._increment_pending_approval()
                    if state_machine is not None:
                        from app.core.task_state_machine import TaskState
                        if state_machine.can_transition_to(TaskState.PAUSED):
                            await state_machine.transition(TaskState.PAUSED, trigger="awaiting_approval")
                    try:
                        decision = await approval_manager.wait_for_decision(
                            req.id,
                            timeout=300,
                            cancelled=lambda: bool(getattr(self._session, "_stop_requested", False)),
                        )
                    finally:
                        pending_count = await self._decrement_pending_approval()
                        if state_machine is not None:
                            from app.core.task_state_machine import TaskState
                            if (
                                pending_count == 0
                                and not getattr(self._session, "_stop_requested", False)
                                and state_machine.can_transition_to(TaskState.PROCESSING)
                            ):
                                await state_machine.transition(TaskState.PROCESSING, trigger="approval_resolved")
                    if decision is None or decision.status.value != "approved":
                        duration = (time.monotonic() - start) * 1000
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
                duration = (time.monotonic() - start) * 1000
                return ToolExecutionResult(
                    tool_name=name,
                    error=f"permission check failed: {e}",
                    success=False,
                    duration_ms=duration,
                    arguments=arguments,
                    tool_call_id=tool_call_id,
                )
        if self._session is not None and getattr(self._session, "_stop_requested", False):
            return ToolExecutionResult(
                tool_name=name,
                error="cancelled",
                success=False,
                arguments=arguments,
                tool_call_id=tool_call_id,
            )
        try:
            result = await asyncio.wait_for(
                self._registry.execute(name, arguments),
                timeout=self._timeout,
            )
            duration = (time.monotonic() - start) * 1000
            if result.startswith(f"Error executing {name}:"):
                return ToolExecutionResult(
                    tool_name=name,
                    error=result,
                    success=False,
                    duration_ms=duration,
                    arguments=arguments,
                    tool_call_id=tool_call_id,
                )
            return ToolExecutionResult(tool_name=name, result=result, duration_ms=duration, arguments=arguments, tool_call_id=tool_call_id)
        except TimeoutError:
            return ToolExecutionResult(tool_name=name, error="timeout", success=False, arguments=arguments, tool_call_id=tool_call_id)
        except asyncio.CancelledError:
            return ToolExecutionResult(tool_name=name, error="cancelled", success=False, arguments=arguments, tool_call_id=tool_call_id)
        except Exception as e:
            return ToolExecutionResult(tool_name=name, error=str(e), success=False, arguments=arguments, tool_call_id=tool_call_id)

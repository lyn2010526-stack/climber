"""Unified Tool Gateway — central dispatch for all tool executions.

- MonkeyCode tool dispatch
- Sidekick-AI unified tool gateway concept
- Cline tool security policy
- Suna tool auto-priority feedback loop

Responsibilities:
1. Permission check (tool enabled, path allowed, dangerous command blocked)
2. Timeout control per tool
3. Execution (builtin / MCP / skill)
4. Retry with fallback
5. Audit logging
6. Outcome recording for tool prioritization learning
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import structlog

from app.core.security_sandbox import PermissionLevel, PermissionOverlay, validate_tool_input
from app.tools import ToolRegistry, tool_registry

logger = structlog.get_logger()


class ToolContext:
    """Context passed to tool executions."""
    def __init__(self, user_id: str = "default-user", session_id: str = "", agent_id: str = ""):
        self.user_id = user_id
        self.session_id = session_id
        self.agent_id = agent_id


class ToolResult:
    """Standardized tool execution result."""
    def __init__(self, output: str, error: str | None = None, duration_ms: float = 0.0, blocked: bool = False):
        self.output = output
        self.error = error
        self.duration_ms = duration_ms
        self.blocked = blocked

    @property
    def success(self) -> bool:
        return self.error is None and not self.blocked


class ToolGateway:
    """Central tool execution gateway with security, timeout, retry, audit, and learning."""

    def __init__(self, registry: ToolRegistry, permission_overlay: PermissionOverlay | None = None, tool_prioritizer: Any | None = None):
        self.registry = registry
        self.permission_overlay = permission_overlay
        self.tool_prioritizer = tool_prioritizer
        self._default_timeouts: dict[str, float] = {
            "run_command": 30.0,
            "browser_navigate": 60.0,
            "web_search": 20.0,
            "fetch_url": 15.0,
        }
        self._max_retries: dict[str, int] = {
            "run_command": 1,
            "web_search": 2,
        }

    async def execute(self, tool_name: str, arguments: dict[str, Any], ctx: ToolContext | None = None) -> ToolResult:
        """Execute a tool with full security pipeline."""
        ctx = ctx or ToolContext()
        start = time.perf_counter()

        # 1. Tool enabled check
        tool_def = self.registry.get_tool(tool_name)
        if tool_def is None:
            duration = (time.perf_counter() - start) * 1000
            self._log_audit(ctx, tool_name, "deny", "not found", duration, blocked=True)
            if self.tool_prioritizer:
                self.tool_prioritizer.record_outcome(tool_name, False, duration)
            return ToolResult(output="", error=f"Tool '{tool_name}' not found", blocked=True)

        # 2. Permission check
        allowed, reason = self._check_permission(tool_name, arguments, ctx)
        if not allowed:
            duration = (time.perf_counter() - start) * 1000
            self._log_audit(ctx, tool_name, "deny", reason, duration, blocked=True)
            if self.tool_prioritizer:
                self.tool_prioritizer.record_outcome(tool_name, False, duration)
            return ToolResult(output="", error=reason, blocked=True)

        # 3. JSON Schema validation
        try:
            if tool_def.parameters:
                validate_tool_input(tool_def.parameters, arguments)
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            self._log_audit(ctx, tool_name, "error", str(e), duration)
            if self.tool_prioritizer:
                self.tool_prioritizer.record_outcome(tool_name, False, duration)
            return ToolResult(output="", error=f"Schema validation error: {e}")

        # 4. Execute with timeout and retry
        timeout = self._default_timeouts.get(tool_name, 10.0)
        max_retries = self._max_retries.get(tool_name, 0)
        last_error = ""
        for attempt in range(max_retries + 1):
            try:
                result = await asyncio.wait_for(
                    self.registry.execute(tool_name, arguments),
                    timeout=timeout,
                )
                duration = (time.perf_counter() - start) * 1000
                self._log_audit(ctx, tool_name, "execute", "ok", duration)
                if self.tool_prioritizer:
                    self.tool_prioritizer.record_outcome(tool_name, True, duration)
                return ToolResult(output=str(result), duration_ms=duration)
            except TimeoutError:
                last_error = f"Timeout after {timeout}s"
                if attempt < max_retries:
                    await asyncio.sleep(0.5 * (attempt + 1))
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries:
                    await asyncio.sleep(0.5 * (attempt + 1))

        duration = (time.perf_counter() - start) * 1000
        self._log_audit(ctx, tool_name, "error", last_error, duration)
        if self.tool_prioritizer:
            self.tool_prioritizer.record_outcome(tool_name, False, duration)
        return ToolResult(output="", error=last_error, duration_ms=duration)

    def _check_permission(self, tool_name: str, arguments: dict[str, Any], ctx: ToolContext) -> tuple[bool, str]:
        """Check permission via overlay."""
        if self.permission_overlay is None:
            return True, "OK"
        action = "execute"
        if tool_name in {"read_file", "write_file", "edit_file", "append_file", "file_exists", "file_info", "file_diff", "list_directory"}:
            action = "read" if tool_name in {"read_file", "file_exists", "file_info", "file_diff", "list_directory"} else "write"
        resource = arguments.get("path") or arguments.get("command") or "*"
        level = self.permission_overlay.evaluate(action, str(resource), agent_id=ctx.agent_id, user_id=ctx.user_id)
        if level == PermissionLevel.DENY:
            return False, f"Permission denied: {action} on {resource}"
        if level == PermissionLevel.ASK:
            return False, f"Permission required: {action} on {resource}"
        return True, "OK"

    def _log_audit(self, ctx: ToolContext, tool_name: str, action: str, reason: str, duration_ms: float, blocked: bool = False) -> None:
        """Log to audit system."""
        try:
            from app.core.security_sandbox import audit_system
            audit_system.log_command(
                session_id=ctx.session_id,
                command=f"{tool_name} {reason}",
                result=reason,
                blocked=blocked,
            )
        except Exception as e:
            logger.warning("tool_gateway.audit_log_failed", error=str(e))


# Global gateway instance
tool_gateway = ToolGateway(registry=tool_registry)


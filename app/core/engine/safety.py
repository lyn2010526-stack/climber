"""Legacy safety helpers.

The production validation chain lives in
``app.core.engine.validation``; this module is kept for import
compatibility only and must not hold its own copy of the command-tool
classification, which previously drifted (missing every native tool).
"""

from __future__ import annotations

from typing import Any

from app.core.engine.validation import _COMMAND_TOOLS as COMMAND_TOOLS
from app.core.engine.validation import _FILE_TOOLS as FILE_TOOLS


def setup_default_permissions(permission_overlay: Any) -> None:
    from app.core.security_sandbox import PermissionLevel, PermissionRule

    defaults = [
        PermissionRule(action="read", resource_pattern="*", level=PermissionLevel.ALLOW, description="Read any file"),
        PermissionRule(action="write", resource_pattern="./data/*", level=PermissionLevel.ALLOW, description="Write to data dir"),
        PermissionRule(action="write", resource_pattern="*.py", level=PermissionLevel.ASK, description="Write Python files"),
        PermissionRule(action="execute", resource_pattern="*", level=PermissionLevel.ASK, description="Execute any command"),
        PermissionRule(action="delete", resource_pattern="*", level=PermissionLevel.DENY, description="Delete forbidden"),
    ]
    permission_overlay.set_defaults(defaults)


def validate_tool_call(
    sandbox: Any,
    permission_overlay: Any,
    agent_mode: Any,
    tool_registry: Any,
    tool_name: str,
    arguments: dict[str, Any],
) -> tuple[bool, str]:
    if agent_mode is not None:
        from app.core.security_sandbox import AgentMode

        if agent_mode == AgentMode.PLAN and tool_name in COMMAND_TOOLS:
            return False, "PLAN mode: command execution is read-only"
        if agent_mode == AgentMode.PLAN and tool_name in FILE_TOOLS:
            param, mode = FILE_TOOLS[tool_name]
            if mode != "read" and tool_name != "edit_file":
                return False, "PLAN mode: file modification is read-only"

    if permission_overlay is not None:
        action = "execute" if tool_name in COMMAND_TOOLS else "read"
        if tool_name in FILE_TOOLS:
            _, mode = FILE_TOOLS[tool_name]
            action = mode
        resource = arguments.get("path") or arguments.get("command") or "*"
        level = permission_overlay.evaluate(action, str(resource), agent_id=None, user_id=None)
        from app.core.security_sandbox import PermissionLevel

        if level == PermissionLevel.DENY:
            return False, f"Permission denied by overlay: {action} on {resource}"
        if level == PermissionLevel.ASK:
            return False, f"Permission required: {action} on {resource}"

    try:
        from app.core.security_sandbox import validate_tool_input

        tool_def = tool_registry.get_tool(tool_name)
        if tool_def and tool_def.parameters:
            validate_tool_input(tool_def.parameters, arguments)
    except Exception as e:
        return False, str(e)

    if sandbox is None:
        return True, "OK"
    try:
        if tool_name in COMMAND_TOOLS:
            cmd = arguments.get("command") or ""
            if isinstance(cmd, str) and cmd:
                ok, reason = sandbox.validate_command(cmd)
                if not ok:
                    return False, reason
        if tool_name in FILE_TOOLS:
            param, mode = FILE_TOOLS[tool_name]
            path = arguments.get(param) or arguments.get("path") or ""
            if isinstance(path, str) and path:
                ok, reason = sandbox.validate_file_access(path, mode)
                if not ok:
                    return False, reason
    except Exception as e:
        return False, f"sandbox validation error: {e}"
    return True, "OK"

from __future__ import annotations

from typing import Any


COMMAND_TOOLS = {"run_command", "shell", "execute_command", "bash"}

FILE_TOOLS: dict[str, tuple[str, str]] = {
    "read_file": ("path", "read"),
    "write_file": ("path", "write"),
    "edit_file": ("path", "write"),
    "append_file": ("path", "write"),
    "file_exists": ("path", "read"),
    "file_info": ("path", "read"),
    "file_diff": ("path", "read"),
    "list_directory": ("dir", "read"),
}


def setup_default_permissions(permission_overlay: Any) -> None:
    from app.core.security_sandbox import PermissionRule, PermissionLevel

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
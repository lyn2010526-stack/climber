"""Tool call validation for the agent engine."""

from __future__ import annotations

from typing import Any

from app.core.session import AgentSession

# Tool names that accept a shell command under a "command" parameter
_COMMAND_TOOLS: set[str] = {"run_command", "shell", "execute_command", "bash"}

# Tool names that perform file IO under path/file parameters
_FILE_TOOLS: dict[str, tuple[str, str]] = {
    "read_file": ("path", "read"),
    "write_file": ("path", "write"),
    "edit_file": ("path", "write"),
    "append_file": ("path", "write"),
    "file_exists": ("path", "read"),
    "file_info": ("path", "read"),
    "file_diff": ("path", "read"),
    "list_directory": ("dir", "read"),
}


def validate_tool_call(
    session: AgentSession,
    tool_name: str,
    arguments: dict[str, Any],
    sandbox: Any = None,
    permission_overlay: Any = None,
    agent_mode: Any = None,
    tool_registry: Any = None,
) -> tuple[bool, Any]:
    """Pre-execution safety check for tool calls.

    Args:
        session: The current agent session.
        tool_name: The name of the tool being called.
        arguments: The tool call arguments.
        sandbox: Optional security sandbox for validation.
        permission_overlay: Optional permission overlay for legacy checks.
        agent_mode: Optional agent mode (PLAN/ACT).
        tool_registry: Optional tool registry for schema validation.

    Returns:
        A tuple of (allowed, reason).
    """
    allowed, reason = _check_plan_mode(agent_mode, tool_name)
    if not allowed:
        return allowed, reason

    approval_key = _approval_key(tool_name, arguments)
    if approval_key not in getattr(session, "_approved_tool_calls", set()):
        allowed, reason = _check_permission_rules(session, tool_name, arguments)
        if not allowed:
            return allowed, reason

        allowed, reason = _check_permission_overlay(
            permission_overlay,
            tool_name,
            arguments,
            agent_id=session.agent_id,
            user_id=session.user_id,
        )
        if not allowed:
            return allowed, reason

    allowed, reason = _check_schema_validation(tool_registry, tool_name, arguments)
    if not allowed:
        return allowed, reason

    return _check_sandbox(sandbox, tool_name, arguments)


def _check_plan_mode(agent_mode: Any, tool_name: str) -> tuple[bool, str]:
    """Check if tool call is allowed in current agent mode.

    Args:
        agent_mode: The current agent mode (PLAN or ACT).
        tool_name: The tool being called.

    Returns:
        A tuple of (allowed, reason).
    """
    if agent_mode is None:
        return True, "OK"
    from app.core.security_sandbox import AgentMode
    if agent_mode == AgentMode.PLAN and tool_name in _COMMAND_TOOLS:
        return False, "PLAN mode: command execution is read-only"
    if agent_mode == AgentMode.PLAN and tool_name in _FILE_TOOLS:
        param, mode = _FILE_TOOLS[tool_name]
        if mode != "read" and tool_name != "edit_file":
            return False, "PLAN mode: file modification is read-only"
    return True, "OK"


def _check_permission_rules(session: AgentSession, tool_name: str, arguments: dict[str, Any]) -> tuple[bool, Any]:
    """Check tool call against permission rules.

    Args:
        session: The agent session with permission config.
        tool_name: The tool being called.
        arguments: The tool call arguments.

    Returns:
        A tuple of (allowed, reason).
    """
    if session.permission_config is not None:
        from app.core.permission_rules import RuleDecision
        decision = session.permission_config.evaluate(tool_name, arguments)
        if decision == RuleDecision.DENY:
            return False, f"Permission denied by rules: {tool_name}"
        if decision == RuleDecision.ASK:
            return False, {
                "requires_approval": True,
                "tool_name": tool_name,
                "arguments": arguments,
                "reason": f"Permission required: {tool_name}",
            }
    return True, "OK"


def _check_permission_overlay(
    permission_overlay: Any,
    tool_name: str,
    arguments: dict[str, Any],
    agent_id: str | None = None,
    user_id: str | None = None,
) -> tuple[bool, Any]:
    """Check tool call against legacy permission overlay.

    Args:
        permission_overlay: The permission overlay instance.
        tool_name: The tool being called.
        arguments: The tool call arguments.

    Returns:
        A tuple of (allowed, reason).
    """
    if permission_overlay is None:
        return True, "OK"
    from app.core.security_sandbox import PermissionLevel
    action = "execute" if tool_name in _COMMAND_TOOLS else "read"
    if tool_name in _FILE_TOOLS:
        _, mode = _FILE_TOOLS[tool_name]
        action = mode
    resource = arguments.get("path") or arguments.get("command") or "*"
    level = permission_overlay.evaluate(action, str(resource), agent_id=agent_id, user_id=user_id)
    if level == PermissionLevel.DENY:
        return False, f"Permission denied by overlay: {action} on {resource}"
    if level == PermissionLevel.ASK:
        return False, {
            "requires_approval": True,
            "tool_name": tool_name,
            "arguments": arguments,
            "action": action,
            "resource": str(resource),
            "reason": f"Permission required: {action} on {resource}",
        }
    return True, "OK"


def _approval_key(tool_name: str, arguments: dict[str, Any]) -> str:
    import json

    return f"{tool_name}:{json.dumps(arguments, sort_keys=True, default=str)}"


def _check_schema_validation(tool_registry: Any, tool_name: str, arguments: dict[str, Any]) -> tuple[bool, str]:
    """Validate tool call arguments against JSON schema.

    Args:
        tool_registry: The tool registry for schema lookup.
        tool_name: The tool being called.
        arguments: The tool call arguments.

    Returns:
        A tuple of (allowed, reason).
    """
    try:
        from app.core.security_sandbox import validate_tool_input
        tool_def = tool_registry.get_tool(tool_name)
        if tool_def and tool_def.parameters:
            validate_tool_input(tool_def.parameters, arguments)
    except Exception as e:
        return False, str(e)
    return True, "OK"


def _check_sandbox(sandbox: Any, tool_name: str, arguments: dict[str, Any]) -> tuple[bool, str]:
    """Validate tool call against security sandbox rules.

    Args:
        sandbox: The security sandbox instance.
        tool_name: The tool being called.
        arguments: The tool call arguments.

    Returns:
        A tuple of (allowed, reason).
    """
    if sandbox is None:
        return True, "OK"
    try:
        if tool_name in _COMMAND_TOOLS:
            cmd = arguments.get("command") or ""
            if isinstance(cmd, str) and cmd:
                result = sandbox.validate_command(cmd)
                if isinstance(result, tuple):
                    ok, reason = result
                    if not ok:
                        return False, reason
        if tool_name in _FILE_TOOLS:
            param, mode = _FILE_TOOLS[tool_name]
            path = arguments.get(param) or arguments.get("path") or ""
            if isinstance(path, str) and path:
                result = sandbox.validate_file_access(path, mode)
                if isinstance(result, tuple):
                    ok, reason = result
                    if not ok:
                        return False, reason
    except Exception as e:
        return False, f"sandbox validation error: {e}"
    return True, "OK"

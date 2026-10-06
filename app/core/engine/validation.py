"""Tool call validation for the agent engine."""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.permission_rules import normalize_tool_name
from app.core.session import AgentSession

# Keep strong references to fire-and-forget audit tasks so they are not
# garbage-collected before they finish.
_BACKGROUND_TASKS: set[asyncio.Task] = set()

# Tool names that accept a shell command under a "command" parameter
# Keys are canonical names — aliases (bash/shell/command/...) resolve via normalize_tool_name
_COMMAND_TOOLS: set[str] = {"run_command"}

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
    "file_delete": ("path", "write"),
}

# Public capability tables for consumers that match against the raw
# (un-normalized) tool name, e.g. the workflow tool-node validator and the
# legacy safety shim.  The canonical tables above are the policy source of
# truth; these mirror the same policy with command aliases listed explicitly
# so no normalize_tool_name call is needed at lookup sites.
COMMAND_TOOLS: frozenset[str] = frozenset(
    {
        "run_command",
        "shell",
        "execute_command",
        "bash",
        "stream_command",
        "container_exec",
    }
)

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


def _command_capability(tool_name: str) -> bool:
    """Whether the tool executes shell commands, resolved through tool name aliases."""
    return normalize_tool_name(tool_name) in _COMMAND_TOOLS


def _file_capability(tool_name: str) -> tuple[str, str] | None:
    """Return (param, mode) for file tools, or None. Resolves tool name aliases."""
    return _FILE_TOOLS.get(normalize_tool_name(tool_name))


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
    audit = _security_audit()
    allowed, reason = _check_plan_mode(agent_mode, tool_name)
    if not allowed:
        _audit_validation(audit, session, tool_name, "plan_denied", reason)
        return allowed, reason

    # A previously approved call skips the approval prompt, never the DENY rules.
    already_approved = _approval_key(tool_name, arguments) in getattr(
        session, "_approved_tool_calls", set()
    )

    allowed, reason = _check_permission_rules(
        session,
        tool_name,
        arguments,
        already_approved=already_approved,
    )
    if not allowed:
        _audit_validation(audit, session, tool_name, "permission_denied", reason)
        return allowed, reason

    if not already_approved:
        allowed, reason = _check_permission_overlay(
            permission_overlay,
            tool_name,
            arguments,
            agent_id=session.agent_id,
            user_id=session.user_id,
        )
        if not allowed:
            _audit_validation(audit, session, tool_name, "overlay_denied", reason)
            return allowed, reason

    allowed, reason = _check_schema_validation(tool_registry, tool_name, arguments)
    if not allowed:
        _audit_validation(audit, session, tool_name, "schema_denied", reason)
        return allowed, reason

    allowed, reason = _check_sandbox(sandbox, tool_name, arguments)
    if not allowed:
        _audit_validation(audit, session, tool_name, "sandbox_denied", reason)
        return allowed, reason
    allowed, reason = _check_script_preflight(tool_name, arguments)
    _audit_validation(audit, session, tool_name, "allowed" if allowed else "script_denied", reason)
    return allowed, reason


def _security_audit() -> Any:
    from app.core.observability.audit import security_audit_chain

    return security_audit_chain


def _audit_validation(audit: Any, session: Any, tool_name: str, decision: str, reason: Any) -> None:
    """Record security decisions without allowing audit storage to affect policy."""
    try:
        audit.log_decision(
            decision_type=decision,
            input_summary=tool_name,
            output_summary=str(reason)[:500],
            rationale="tool pre-execution validation",
            agent_id=str(getattr(session, "agent_id", "")),
            session_id=str(getattr(session, "session_id", "")),
        )
    except Exception:
        # AuditChain itself buffers persistence failures; this final guard keeps
        # an observability outage from changing a fail-closed security result.
        return
    _mirror_durable_permission_audit(session, tool_name, decision, reason)


def _mirror_durable_permission_audit(
    session: Any, tool_name: str, decision: str, reason: Any
) -> None:
    """Mirror the decision onto the durable audit table without blocking policy."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    async def _write() -> None:
        from app.core.observability.audit_store import audit_log

        await audit_log.log_permission_decision(
            session_id=getattr(session, "session_id", None),
            user_id=getattr(session, "user_id", None),
            tool_name=tool_name,
            allowed=decision == "allowed",
            reason=str(reason)[:500],
        )

    try:
        task = loop.create_task(_write())
    except Exception:
        return
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)


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

    if agent_mode != AgentMode.PLAN:
        return True, "OK"
    if _command_capability(tool_name):
        return False, "PLAN mode: command execution is read-only"
    file_capability = _file_capability(tool_name)
    if file_capability is not None:
        _, mode = file_capability
        if mode != "read" and normalize_tool_name(tool_name) != "edit_file":
            return False, "PLAN mode: file modification is read-only"
    return True, "OK"


def _check_permission_rules(
    session: AgentSession,
    tool_name: str,
    arguments: dict[str, Any],
    already_approved: bool = False,
) -> tuple[bool, Any]:
    """Check tool call against permission rules.

    DENY always wins, including for calls the user already approved; approval only
    suppresses the ASK prompt.

    Args:
        session: The agent session with permission config.
        tool_name: The tool being called.
        arguments: The tool call arguments.
        already_approved: Whether this exact call was approved earlier in the session.

    Returns:
        A tuple of (allowed, reason).
    """
    if session.permission_config is not None:
        from app.core.permission_rules import RuleDecision

        decision = session.permission_config.evaluate(tool_name, arguments)
        if decision == RuleDecision.DENY:
            return False, f"Permission denied by rules: {tool_name}"
        if decision == RuleDecision.ASK and not already_approved:
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

    action = "execute" if _command_capability(tool_name) else "read"
    file_capability = _file_capability(tool_name)
    if file_capability is not None:
        action = file_capability[1]
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


def _check_schema_validation(
    tool_registry: Any, tool_name: str, arguments: dict[str, Any]
) -> tuple[bool, str]:
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
        if _command_capability(tool_name):
            cmd = arguments.get("command") or ""
            if isinstance(cmd, str) and cmd:
                result = sandbox.validate_command(cmd)
                if isinstance(result, tuple):
                    ok, reason = result
                    if not ok:
                        return False, reason
        file_capability = _file_capability(tool_name)
        if file_capability is not None:
            param, mode = file_capability
            # The canonical table pins one parameter key per tool, but real
            # implementations differ (list_files uses "directory"), so probe
            # the documented aliases as well before giving up.
            path = arguments.get(param) or arguments.get("directory") or arguments.get("path") or ""
            if isinstance(path, str) and path:
                result = sandbox.validate_file_access(path, mode)
                if isinstance(result, tuple):
                    ok, reason = result
                    if not ok:
                        return False, reason
    except Exception as e:
        return False, f"sandbox validation error: {e}"
    return True, "OK"


def _check_script_preflight(tool_name: str, arguments: dict[str, Any]) -> tuple[bool, str]:
    """Statically test executable script payloads before the sandbox runs them."""
    code = arguments.get("code") or arguments.get("script")
    if not isinstance(code, str):
        return True, "OK"
    from app.core.security_sandbox import CodeSandbox

    result = CodeSandbox().preflight_script(code)
    if not result.allowed:
        return False, f"Script preflight blocked: {result.reason}"
    return True, "OK"

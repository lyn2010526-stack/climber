"""Tool capability policy for workflow tool nodes.

Workflow tool nodes historically executed tools with no pre-flight
validation, giving a workflow author the same reach as an interactive
agent but without the sandbox chain.  This module applies a default-deny
capability allowlist so that high-risk tools (file writes, arbitrary
shell, docker) are rejected unless explicitly enabled, and any allowed
tool still goes through schema + sandbox checks.
"""

from __future__ import annotations

import structlog
from typing import Any

logger = structlog.get_logger()

# Tools that modify the local filesystem.
FILE_WRITE_TOOLS: frozenset[str] = frozenset({
    "write_file", "edit_file", "append_file", "apply_patch",
})

# Tools that execute arbitrary shell commands.
SHELL_TOOLS: frozenset[str] = frozenset({
    "run_command", "shell", "execute_command", "bash",
    "stream_command",
})

# Tools that reach into containers / system-level execution.
DOCKER_TOOLS: frozenset[str] = frozenset({
    "container_exec", "docker",
})

# Tools that are rejected by default in workflow tool nodes.  A workflow
# author must explicitly opt in via workflow-level tool capabilities.
DEFAULT_DENIED_TOOLS: frozenset[str] = frozenset().union(
    FILE_WRITE_TOOLS, SHELL_TOOLS, DOCKER_TOOLS,
)

# Tools that are always allowed in workflow tool nodes.
DEFAULT_ALLOWED_TOOLS: frozenset[str] = frozenset({
    "read_file", "list_files", "file_exists", "file_info", "file_diff",
    "get_datetime", "calculator", "web_search", "fetch_url",
    "get_weather", "translate", "wikipedia_summary", "summarize",
    "base64_encode", "json_get", "simulate_experiment",
})


def _parse_tool_capabilities(workflow_capabilities: Any) -> set[str]:
    """Resolve a workflow's tool capability declaration to a tool set.

    Accepts None (default deny everything not in DEFAULT_ALLOWED_TOOLS),
    a string of tool names, or a list of tool names.  A leading "+" or
    "-" per item can add or remove specific tools relative to defaults.
    """
    if workflow_capabilities is None:
        return set(DEFAULT_ALLOWED_TOOLS)

    raw = workflow_capabilities
    if isinstance(raw, str):
        raw = [part.strip() for part in raw.split(",") if part.strip()]
    if not isinstance(raw, list):
        raise ValueError(
            "tool_capabilities must be a string or list of tool names"
        )

    resolved = set(DEFAULT_ALLOWED_TOOLS)
    for item in raw:
        if not isinstance(item, str):
            continue
        item = item.strip()
        if not item:
            continue
        if item.startswith("+"):
            resolved.add(item[1:].strip())
        elif item.startswith("-"):
            resolved.discard(item[1:].strip())
        else:
            resolved.add(item)
    return resolved


def is_tool_allowed(tool_name: str, allowed_tools: set[str]) -> bool:
    """Check whether a tool is present in the resolved capability set."""
    return tool_name in allowed_tools


def build_workflow_tool_validator(
    tool_registry: Any,
    sandbox: Any = None,
    permission_overlay: Any = None,
    capabilities: Any = None,
) -> Any:
    """Build a validator callback for ParallelToolExecutor.

    The callback signature matches the ParallelToolExecutor Validator:
    ``(tool_name, arguments) -> (allowed, reason)``.  The policy chain is:

    1. Capability allowlist (default-deny high-risk tools).
    2. JSON schema validation against the tool definition.
    3. Sandbox checks (command allowlist, file access scope).
    """
    allowed_tools = _parse_tool_capabilities(capabilities)

    def validator(tool_name: str, arguments: dict[str, Any]) -> tuple[bool, str]:
        if not is_tool_allowed(tool_name, allowed_tools):
            logger.warning(
                "workflow.tool_denied",
                tool=tool_name,
                reason="not_in_capability_allowlist",
            )
            return False, (
                f"workflow tool '{tool_name}' is disabled by default; "
                "add it to tool_capabilities to enable"
            )

        try:
            from app.core.security_sandbox import validate_tool_input

            tool_def = tool_registry.get_tool(tool_name) if tool_registry else None
            if tool_def and tool_def.parameters:
                validate_tool_input(tool_def.parameters, arguments)
        except Exception as e:
            logger.warning(
                "workflow.tool_denied",
                tool=tool_name,
                reason="schema_validation",
                error=str(e),
            )
            return False, f"invalid tool arguments: {e}"

        if sandbox is None:
            return True, "OK"
        try:
            from app.core.engine.safety import COMMAND_TOOLS, FILE_TOOLS

            if tool_name in COMMAND_TOOLS:
                cmd = arguments.get("command") or ""
                if isinstance(cmd, str) and cmd:
                    ok, reason = sandbox.validate_command(cmd)
                    if not ok:
                        logger.warning(
                            "workflow.tool_denied",
                            tool=tool_name,
                            reason="command_policy",
                            detail=reason,
                        )
                        return False, reason
            if tool_name in FILE_TOOLS:
                param, mode = FILE_TOOLS[tool_name]
                path = arguments.get(param) or arguments.get("path") or ""
                if isinstance(path, str) and path:
                    ok, reason = sandbox.validate_file_access(path, mode)
                    if not ok:
                        logger.warning(
                            "workflow.tool_denied",
                            tool=tool_name,
                            reason="file_access",
                            detail=reason,
                        )
                        return False, reason
        except Exception as e:
            return False, f"sandbox validation error: {e}"
        return True, "OK"

    return validator

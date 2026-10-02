"""Legacy safety entry points.

Historical duplicate of the tool-call validation chain. The single
implementation now lives in :mod:`app.core.engine.validation`; this module
keeps the old import surface as a thin wrapper so existing callers
(``COMMAND_TOOLS``/``FILE_TOOLS`` consumers and legacy-signature
``validate_tool_call`` callers) keep working. New code must import from
``app.core.engine.validation`` directly.
"""

from __future__ import annotations

from typing import Any

from app.core.engine.validation import (
    _COMMAND_TOOLS as COMMAND_TOOLS,
    _FILE_TOOLS as FILE_TOOLS,
    validate_tool_call as _validate_tool_call,
)

__all__ = [
    "COMMAND_TOOLS",
    "FILE_TOOLS",
    "setup_default_permissions",
    "validate_tool_call",
]


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


class _ShimSession:
    """Duck-typed session for callers that have no AgentSession (legacy API)."""

    permission_config: Any = None

    def __init__(self) -> None:
        self._approved_tool_calls: set[str] = set()
        self.agent_id: str | None = None
        self.user_id: str | None = None


def validate_tool_call(
    sandbox: Any,
    permission_overlay: Any,
    agent_mode: Any,
    tool_registry: Any,
    tool_name: str,
    arguments: dict[str, Any],
) -> tuple[bool, str]:
    """Legacy-signature wrapper around app.core.engine.validation.

    Normalises approval-request reasons (dict form) back to the legacy
    ``(False, "Permission required: ...")`` string form.
    """
    allowed, reason = _validate_tool_call(
        _ShimSession(),
        tool_name,
        arguments,
        sandbox=sandbox,
        permission_overlay=permission_overlay,
        agent_mode=agent_mode,
        tool_registry=tool_registry,
    )
    if isinstance(reason, dict):
        return allowed, str(reason.get("reason", "Permission required"))
    return allowed, reason

"""Permission middleware — fine-grained tool access control with audit logging.

Adds middleware-based permission checking that can:
- Enforce tool-specific policies
- Log all permission decisions
- Support rate limiting per tool
- Integrate with the existing PermissionController
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import TYPE_CHECKING, Any

import structlog

from app.core.middleware import MiddlewareBase

if TYPE_CHECKING:
    from app.core.agent_engine import AgentEngine, AgentSession

logger = structlog.get_logger()


class PermissionMiddleware(MiddlewareBase):
    """Middleware for fine-grained tool permission control.

    Features:
    - Per-tool rate limiting
    - Audit logging of all permission decisions
    - Tool-specific allow/deny lists
    - Integration with existing PermissionController
    """

    def __init__(
        self,
        max_calls_per_minute: int = 60,
        denied_tools: list[str] | None = None,
        allowed_tools: list[str] | None = None,
        audit_log: bool = True,
    ):
        self.max_calls_per_minute = max_calls_per_minute
        self.denied_tools = set(denied_tools or [])
        self.allowed_tools = set(allowed_tools or [])  # empty = all allowed
        self.audit_log = audit_log
        self._call_counts: dict[str, list[float]] = defaultdict(list)

    def _check_rate_limit(self, tool_name: str) -> bool:
        """Check if tool call rate is within limits."""
        now = time.time()
        window_start = now - 60

        # Clean old entries
        self._call_counts[tool_name] = [
            t for t in self._call_counts[tool_name] if t > window_start
        ]

        # Check limit
        if len(self._call_counts[tool_name]) >= self.max_calls_per_minute:
            return False

        # Record this call
        self._call_counts[tool_name].append(now)
        return True

    async def on_check_permission(
        self,
        engine: AgentEngine,
        session: AgentSession,
        input_kwargs: dict[str, Any],
        next_handler: Any,
    ) -> tuple[bool, str]:
        """Check tool permission with rate limiting and audit logging."""
        tool_name = input_kwargs.get("tool_name", "unknown")

        # Check explicit deny list
        if tool_name in self.denied_tools:
            reason = f"Tool '{tool_name}' is in the denied list"
            if self.audit_log:
                logger.warning(
                    "permission.denied",
                    tool=tool_name,
                    reason=reason,
                    session_id=session.session_id,
                )
            return False, reason

        # Check explicit allow list (if configured)
        if self.allowed_tools and tool_name not in self.allowed_tools:
            reason = f"Tool '{tool_name}' is not in the allowed list"
            if self.audit_log:
                logger.warning(
                    "permission.denied",
                    tool=tool_name,
                    reason=reason,
                    session_id=session.session_id,
                )
            return False, reason

        # Check rate limit
        if not self._check_rate_limit(tool_name):
            reason = f"Tool '{tool_name}' rate limit exceeded ({self.max_calls_per_minute}/min)"
            if self.audit_log:
                logger.warning(
                    "permission.rate_limited",
                    tool=tool_name,
                    session_id=session.session_id,
                )
            return False, reason

        # Delegate to next handler (existing permission system)
        allowed, reason = await next_handler()

        if self.audit_log:
            if allowed:
                logger.info(
                    "permission.granted",
                    tool=tool_name,
                    session_id=session.session_id,
                )
            else:
                logger.warning(
                    "permission.denied",
                    tool=tool_name,
                    reason=reason,
                    session_id=session.session_id,
                )

        return allowed, reason

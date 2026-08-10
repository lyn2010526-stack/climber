"""Tool rules solver — reference: Letta ToolRulesSolver.

Manages tool execution rules:
- Terminal tools: cannot be called with other tools in same turn
- Init tools: must be called first in a sequence
- Continue tools: can only be called after another tool
- Failure prevention: disallow retry of failed tools within a turn
- Heartbeat control: manages multi-step execution rhythm
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import structlog

logger = structlog.get_logger()


class ToolRuleType(StrEnum):
    TERMINAL = "terminal"  # Cannot combine with other tools
    INIT = "init"  # Must be first in sequence
    CONTINUE = "continue"  # Must follow another tool
    NORMAL = "normal"  # No special rules
    CONDITIONAL = "conditional"  # Depends on previous tool result


@dataclass
class ToolRule:
    """Defines a rule for a tool."""
    tool_name: str
    rule_type: ToolRuleType = ToolRuleType.NORMAL
    requires: list[str] = field(default_factory=list)  # Must have been called before
    excludes: list[str] = field(default_factory=list)  # Cannot be called together with
    max_retries: int = 0  # Max retries after failure
    description: str = ""


@dataclass
class ToolCallRecord:
    """Record of a tool call within a turn."""
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: str | None = None
    result_summary: str = ""
    order: int = 0


@dataclass
class RulesCheckResult:
    """Result of checking a tool call against rules."""
    allowed: bool
    reason: str = ""
    violated_rules: list[str] = field(default_factory=list)


class ToolRulesSolver:
    """Validates tool calls against defined rules.

    Reference: Letta ToolRulesSolver — enforces tool dependency ordering,
    prevents incompatible combinations, and tracks failure history.
    """

    def __init__(self) -> None:
        self._rules: dict[str, ToolRule] = {}
        self._call_history: list[ToolCallRecord] = []
        self._failed_tools: set[str] = set()  # Tools that failed this turn
        self._call_order = 0

    def register_rule(self, rule: ToolRule) -> None:
        """Register a tool rule."""
        self._rules[rule.tool_name] = rule

    def register_rules(self, rules: list[ToolRule]) -> None:
        """Register multiple tool rules."""
        for rule in rules:
            self.register_rule(rule)

    def reset_turn(self) -> None:
        """Reset state for a new turn."""
        self._call_history = []
        self._failed_tools = set()
        self._call_order = 0

    def record_result(self, tool_name: str, success: bool, error: str | None = None, result: str = "") -> None:
        """Record a tool execution result."""
        self._call_order += 1
        self._call_history.append(ToolCallRecord(
            tool_name=tool_name,
            success=success,
            error=error,
            result_summary=result[:200] if result else "",
            order=self._call_order,
        ))
        if not success:
            self._failed_tools.add(tool_name)

    def check_tool_call(self, tool_name: str, *, batch: list[str] | None = None) -> RulesCheckResult:
        """Check if a tool call is allowed given current state and rules.

        Args:
            tool_name: Tool to check
            batch: All tools being called in the same turn (for TERMINAL check)

        Returns:
            RulesCheckResult with allowed status and reason
        """
        rule = self._rules.get(tool_name)
        violated: list[str] = []

        if not rule:
            return RulesCheckResult(allowed=True)

        # Check failure retry rule
        if tool_name in self._failed_tools and rule.max_retries == 0:
            violated.append(f"{tool_name} already failed this turn (max_retries=0)")

        # Check terminal rule — cannot combine with others
        if rule.rule_type == ToolRuleType.TERMINAL and batch and len(batch) > 1:
            violated.append(f"{tool_name} is terminal and cannot be combined with other tools")

        # Check init rule — must be first
        if rule.rule_type == ToolRuleType.INIT and self._call_history:
            violated.append(f"{tool_name} is init tool but other tools already called")

        # Check continue rule — must follow another tool
        if rule.rule_type == ToolRuleType.CONTINUE and not self._call_history:
            violated.append(f"{tool_name} is continue tool but no prior tool calls")

        # Check requires constraints
        called_tools = {r.tool_name for r in self._call_history}
        for req in rule.requires:
            if req not in called_tools:
                violated.append(f"{tool_name} requires {req} to have been called first")

        # Check excludes constraints
        if batch:
            for exc in rule.excludes:
                if exc in batch and exc != tool_name:
                    violated.append(f"{tool_name} cannot be called together with {exc}")

        if violated:
            return RulesCheckResult(
                allowed=False,
                reason=f"Tool '{tool_name}' violated {len(violated)} rule(s)",
                violated_rules=violated,
            )

        return RulesCheckResult(allowed=True)

    def filter_batch(self, tool_names: list[str]) -> tuple[list[str], list[str]]:
        """Filter a batch of tool calls, removing those that violate rules.

        Returns:
            Tuple of (allowed, rejected) tool names
        """
        allowed: list[str] = []
        rejected: list[str] = []

        for name in tool_names:
            result = self.check_tool_call(name, batch=tool_names)
            if result.allowed:
                allowed.append(name)
            else:
                rejected.append(name)
                logger.debug("tool_rules.rejected", tool=name, reason=result.reason)

        return allowed, rejected

    def get_recommended_next(self, available_tools: list[str]) -> list[str]:
        """Get tools that are valid to call next, given current state."""
        return [
            t for t in available_tools
            if self.check_tool_call(t).allowed
        ]

    def get_history_summary(self) -> dict[str, Any]:
        """Get summary of tool call history this turn."""
        return {
            "total_calls": len(self._call_history),
            "successful": sum(1 for r in self._call_history if r.success),
            "failed": sum(1 for r in self._call_history if not r.success),
            "failed_tools": list(self._failed_tools),
            "call_order": [r.tool_name for r in self._call_history],
        }


class HeartbeatController:
    """Controls multi-step execution rhythm using heartbeat requests.

    Reference: Letta heartbeat mechanism — allows model to signal
    "I'm done for now" vs "continue executing" without extra API calls.
    """

    def __init__(self, max_heartbeats: int = 5, heartbeat_token: str = "<heartbeat>") -> None:
        self._max_heartbeats = max_heartbeats
        self._heartbeat_token = heartbeat_token
        self._heartbeat_count = 0

    def reset(self) -> None:
        self._heartbeat_count = 0

    @property
    def is_exhausted(self) -> bool:
        return self._heartbeat_count >= self._max_heartbeats

    @property
    def remaining(self) -> int:
        return max(0, self._max_heartbeats - self._heartbeat_count)

    def record_heartbeat(self) -> bool:
        """Record a heartbeat. Returns False if limit reached."""
        if self._heartbeat_count >= self._max_heartbeats:
            return False
        self._heartbeat_count += 1
        return True

    def check_heartbeat_signal(self, content: str) -> bool:
        """Check if model output contains heartbeat signal."""
        if self._heartbeat_token in content:
            return self.record_heartbeat()
        return True  # Not a heartbeat signal, no-op

    def get_status(self) -> dict[str, Any]:
        return {
            "count": self._heartbeat_count,
            "max": self._max_heartbeats,
            "remaining": self.remaining,
            "exhausted": self.is_exhausted,
        }

"""Permission enforcement at the tool dispatch layer (audit P2-5).

``app/core/permission_rules.py`` can return a decision, and
``app/core/engine/validation.py`` turns that decision into a block, but the
engine is the only caller. Any other path that reaches ``ToolRegistry`` --
``app/workflow/engine.py:427`` builds ``ParallelToolExecutor(registry)`` with no
validator, and ``agent_engine``'s debug-retry callback calls
``tool_registry.execute`` directly -- executes the tool with the rules ignored.
A permission the tool layer ignores is not a permission, so the gate lives
here, one layer below every caller.

Scope of the gate:

* **DENY** is enforced. A hard-deny has no legitimate execution path, so
  blocking it here cannot break an approval flow.
* **ASK** passes through by default. ASK means "ask the user", and the hosts
  that implement that (the engine's HITL flow via
  ``session._approved_tool_calls``) sit above this layer. Hosts that would
  rather fail closed can pass ``block_ask=True`` or an ``approval_checker``.

Unconfigured registries stay ungated, so an isolated test registry and the
workflow engine keep their current behaviour until a host opts in.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.core.permission_rules import PermissionConfig, PermissionRule, RuleDecision

# (tool_name, arguments) -> True when the host has already obtained approval.
ApprovalChecker = Callable[[str, dict[str, Any]], bool]

# Retrieval tools are read-only, so the default posture allows them outright
# instead of inheriting DEFAULT mode's "ask for anything unlisted".
READ_ONLY_TOOLS = ("grep", "glob")


def default_dispatch_config() -> PermissionConfig:
    """``get_default_config()`` plus read-only allowances for the retrieval tools.

    ``PermissionConfig.evaluate`` in DEFAULT mode allows a fixed list that
    predates these tools, so ``grep`` would otherwise evaluate to ASK. Built
    here rather than in ``app/core/permission_rules.py`` so the core rule set
    stays untouched.
    """
    from app.core.permission_rules import get_default_config

    config = get_default_config()
    existing = {(rule.tool.lower(), rule.pattern) for rule in config.rules}
    for name in READ_ONLY_TOOLS:
        if (name, None) not in existing:
            config.rules.append(PermissionRule(RuleDecision.ALLOW, name))
    return config


@dataclass
class GateVerdict:
    """Outcome of one gate evaluation."""

    decision: RuleDecision
    reason: str = ""

    @property
    def blocked(self) -> bool:
        return self.decision is RuleDecision.DENY


class ToolPermissionGate:
    """Applies a :class:`PermissionConfig` at tool dispatch time."""

    def __init__(
        self,
        config: PermissionConfig,
        block_ask: bool = False,
        approval_checker: ApprovalChecker | None = None,
    ) -> None:
        self._config = config
        self._block_ask = block_ask
        self._approval_checker = approval_checker

    @property
    def config(self) -> PermissionConfig:
        return self._config

    def set_config(self, config: PermissionConfig) -> None:
        self._config = config

    def check(self, tool_name: str, arguments: dict[str, Any] | None = None) -> GateVerdict:
        """Evaluate one call without executing it."""
        decision = self._config.evaluate(tool_name, arguments or {})
        if decision is RuleDecision.ALLOW:
            return GateVerdict(decision)
        if decision is RuleDecision.DENY:
            return GateVerdict(decision, f"Permission denied by rules: {tool_name}")
        if self._approval_checker is not None:
            try:
                if self._approval_checker(tool_name, arguments or {}):
                    return GateVerdict(RuleDecision.ALLOW)
            except Exception as exc:  # a broken approval hook must fail closed
                return GateVerdict(RuleDecision.DENY, f"Approval check failed for {tool_name}: {exc}")
        if self._block_ask:
            return GateVerdict(RuleDecision.DENY, f"Permission required: {tool_name}")
        return GateVerdict(RuleDecision.ASK)


__all__ = ["READ_ONLY_TOOLS", "GateVerdict", "ToolPermissionGate", "default_dispatch_config"]

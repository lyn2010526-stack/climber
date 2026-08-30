# app/core/permission_controller.py
"""Unified permission controller — single entry point for all tool permission checks.

7 permission levels (inspired by Claude Code):
1. READ_ONLY: only read operations allowed
2. STANDARD: read + safe writes, deny dangerous commands
3. ACCEPT_EDITS: allow file modifications without asking
4. PLAN: only planning, no execution
5. AUTO: allow everything (full autonomous)
6. MANUAL: ask for approval on every write operation
7. BYPASS: skip all checks (emergency only)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import StrEnum

logger = logging.getLogger(__name__)


class PermissionMode(StrEnum):
    READ_ONLY = "read_only"
    STANDARD = "standard"
    ACCEPT_EDITS = "accept_edits"
    PLAN = "plan"
    AUTO = "auto"
    MANUAL = "manual"
    BYPASS = "bypass"


@dataclass
class PermissionDecision:
    allowed: bool
    reason: str = ""
    requires_approval: bool = False
    risk_level: str = "low"  # low, medium, high


@dataclass
class ToolRule:
    tool_pattern: str  # glob or exact name
    allowed: bool = True
    requires_approval: bool = False


# Dangerous patterns that are always blocked unless BYPASS
DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/",
    r"rm\s+-rf\s+~",
    r"curl.*\|\s*(ba)?sh",
    r"wget.*\|\s*(ba)?sh",
    r"git\s+push\s+--force",
    r"dd\s+if=.*of=/dev/",
    r":\(\)\{\s*:\|:\s*&\s*\};:",  # fork bomb
    r"chmod\s+-R\s+777",
]

# Tools that require elevated permission
HIGH_RISK_TOOLS = {"shell_exec", "write_file", "delete_file", "database_exec", "api_call"}
READ_ONLY_TOOLS = {"read_file", "search", "list_dir", "query"}

# Inline risk levels the LLM may self-report via the injected schema property.
SECURITY_RISK_PARAM = "security_risk"
SECURITY_RISK_LEVELS = ("LOW", "MEDIUM", "HIGH")


def inject_security_risk_param(parameters: dict) -> dict:
    """Return a copy of a tool schema with an optional security_risk property.

    OpenHands-style inline risk assessment: the LLM fills this in while
    generating the action (zero extra LLM calls), and the permission layer
    escalates HIGH assessments to human approval. Idempotent and
    non-destructive to the input schema.
    """
    out = dict(parameters or {})
    props = dict(out.get("properties") or {})
    if SECURITY_RISK_PARAM not in props:
        props[SECURITY_RISK_PARAM] = {
            "type": "string",
            "enum": list(SECURITY_RISK_LEVELS),
            "description": (
                "Your assessment of this specific action's security risk. "
                "HIGH for destructive/irreversible operations, credential or "
                "secret access, or actions affecting shared state."
            ),
        }
    out["properties"] = props
    if "required" in out:
        out["required"] = list(out["required"])
    return out


def extract_security_risk(arguments: dict) -> str | None:
    """Read the LLM's inline risk level from tool arguments, if present."""
    value = (arguments or {}).get(SECURITY_RISK_PARAM)
    if not isinstance(value, str):
        return None
    level = value.strip().upper()
    return level if level in SECURITY_RISK_LEVELS else None


class PermissionController:
    """Consolidates permission checks from 3 fragmented systems."""

    def __init__(self):
        self._mode = PermissionMode.STANDARD
        self._rules: list[ToolRule] = []
        self._dangerous_regex = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS]
        self._custom_patterns: list[re.Pattern] = []

    def set_mode(self, mode: PermissionMode):
        self._mode = mode

    def get_mode(self) -> PermissionMode:
        return self._mode

    def add_rule(self, tool_pattern: str, allowed: bool = True, requires_approval: bool = False):
        self._rules.append(ToolRule(tool_pattern=tool_pattern, allowed=allowed, requires_approval=requires_approval))

    def add_dangerous_pattern(self, pattern: str):
        self._custom_patterns.append(re.compile(pattern, re.IGNORECASE))

    def evaluate(self, tool_name: str, arguments: dict) -> PermissionDecision:
        """Evaluate whether a tool call should be allowed."""
        # BYPASS mode: allow everything
        if self._mode == PermissionMode.BYPASS:
            return PermissionDecision(allowed=True, reason="BYPASS mode")

        decision = self._evaluate_static(tool_name, arguments)
        # Inline LLM risk escalation: a HIGH self-assessment forces approval.
        # Escalation only — LOW/MEDIUM never weaken the static decision.
        if (
            decision.allowed
            and not decision.requires_approval
            and extract_security_risk(arguments) == "HIGH"
        ):
            return PermissionDecision(
                allowed=True,
                requires_approval=True,
                reason=f"LLM assessed action risk as HIGH: {tool_name}",
                risk_level="high",
            )
        return decision

    def _evaluate_static(self, tool_name: str, arguments: dict) -> PermissionDecision:
        """Static name/pattern/mode-based evaluation (original logic)."""
        # Check tool-specific rules first (highest priority)
        for rule in self._rules:
            if self._match_pattern(tool_name, rule.tool_pattern):
                if not rule.allowed:
                    return PermissionDecision(allowed=False, reason=f"Tool '{tool_name}' denied by rule")
                if rule.requires_approval:
                    return PermissionDecision(allowed=True, requires_approval=True, reason=f"Tool '{tool_name}' requires approval")

        # Check dangerous patterns in arguments
        args_str = str(arguments)
        for pattern in self._dangerous_regex + self._custom_patterns:
            if pattern.search(args_str):
                return PermissionDecision(allowed=False, reason=f"Dangerous pattern detected: {pattern.pattern}", risk_level="high")

        # Mode-based evaluation
        if self._mode == PermissionMode.READ_ONLY:
            if tool_name in READ_ONLY_TOOLS:
                return PermissionDecision(allowed=True)
            return PermissionDecision(allowed=False, reason="READ_ONLY mode: only read operations allowed")

        if self._mode == PermissionMode.PLAN:
            return PermissionDecision(allowed=False, reason="PLAN mode: execution disabled, only planning")

        if self._mode == PermissionMode.MANUAL:
            if tool_name in HIGH_RISK_TOOLS:
                return PermissionDecision(allowed=True, requires_approval=True, reason="MANUAL mode: high-risk tool requires approval")
            return PermissionDecision(allowed=True)

        if self._mode == PermissionMode.AUTO:
            return PermissionDecision(allowed=True, reason="AUTO mode: all operations allowed")

        # STANDARD mode (default)
        if tool_name in HIGH_RISK_TOOLS:
            return PermissionDecision(allowed=True, requires_approval=False, risk_level="medium")
        return PermissionDecision(allowed=True)

    def _match_pattern(self, name: str, pattern: str) -> bool:
        """Match tool name against a glob pattern."""
        import fnmatch
        return fnmatch.fnmatch(name, pattern)

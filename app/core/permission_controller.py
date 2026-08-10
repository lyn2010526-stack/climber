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

"""Meta-Cognition Monitor — continuous self-monitoring of agent reasoning.

Detects: redundant tool calls, hallucination patterns, context overflow,
goal drift, tool misuse.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class DefectType(StrEnum):
    REDUNDANT_CALL = "redundant_call"
    HALLUCINATION_RISK = "hallucination_risk"
    CONTEXT_OVERFLOW = "context_overflow"
    GOAL_DRIFT = "goal_drift"
    TOOL_MISUSE = "tool_misuse"
    INSUFFICIENT_CAPABILITY = "insufficient_capability"


@dataclass
class DefectReport:
    type: DefectType
    description: str
    severity: float  # 0.0-1.0
    iteration: int
    suggestion: str


@dataclass
class MonitoringResult:
    defects: list[DefectReport] = field(default_factory=list)
    health_score: float = 1.0  # 1.0 = perfect, 0.0 = critical
    should_stop: bool = False
    should_escalate: bool = False

    @property
    def has_critical(self) -> bool:
        return any(d.severity > 0.8 for d in self.defects)


class MetaCognitionMonitor:
    """Analyzes agent execution trace for defects and health issues."""

    def __init__(self):
        self._call_history: list[dict[str, Any]] = []
        self._goal: str = ""
        self._token_budget: int = 8000
        self._token_used: int = 0

    def reset(self, goal: str, token_budget: int = 8000) -> None:
        self._call_history.clear()
        self._goal = goal
        self._token_budget = token_budget
        self._token_used = 0

    def record_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        result: str,
        iteration: int,
    ) -> None:
        self._call_history.append({
            "tool": tool_name,
            "args": arguments,
            "result": result[:500],
            "iteration": iteration,
        })

    def record_token_usage(self, tokens: int) -> None:
        self._token_used += tokens

    def analyze(self, current_iteration: int, current_output: str = "") -> MonitoringResult:
        """Run all defect detection checks."""
        defects: list[DefectReport] = []

        defects.extend(self._check_redundant_calls(current_iteration))
        defects.extend(self._check_context_overflow())
        defects.extend(self._check_goal_drift(current_output))
        defects.extend(self._check_tool_misuse())
        defects.extend(self._check_capability_gap(current_output))

        health = self._compute_health(defects)
        should_stop = health < 0.3 or any(d.severity > 0.9 for d in defects)
        should_escalate = health < 0.9

        return MonitoringResult(
            defects=defects,
            health_score=health,
            should_stop=should_stop,
            should_escalate=should_escalate,
        )

    def _check_redundant_calls(self, iteration: int) -> list[DefectReport]:
        defects = []
        seen: dict[str, int] = {}
        for call in self._call_history:
            key = f"{call['tool']}:{sorted(call['args'].items())}"
            seen[key] = seen.get(key, 0) + 1

        for key, count in seen.items():
            if count >= 3:
                defects.append(DefectReport(
                    type=DefectType.REDUNDANT_CALL,
                    description=f"Tool '{key.split(':')[0]}' called {count} times with same arguments",
                    severity=min(0.3 + 0.2 * count, 0.95),
                    iteration=iteration,
                    suggestion="Try a fundamentally different approach or stop retrying",
                ))
        return defects

    def _check_context_overflow(self) -> list[DefectReport]:
        defects = []
        usage_ratio = self._token_used / max(self._token_budget, 1)
        if usage_ratio > 0.9:
            defects.append(DefectReport(
                type=DefectType.CONTEXT_OVERFLOW,
                description=f"Token usage at {usage_ratio:.0%} ({self._token_used}/{self._token_budget})",
                severity=0.9,
                iteration=len(self._call_history),
                suggestion="Trigger context compression immediately or stop current branch",
            ))
        elif usage_ratio > 0.7:
            defects.append(DefectReport(
                type=DefectType.CONTEXT_OVERFLOW,
                description=f"Token usage at {usage_ratio:.0%} — approaching limit",
                severity=0.5,
                iteration=len(self._call_history),
                suggestion="Consider reducing tool calls or triggering early compression",
            ))
        return defects

    def _check_goal_drift(self, output: str) -> list[DefectReport]:
        if not self._goal or not output:
            return []
        goal_words = set(self._goal.lower().split())
        output_words = set(output.lower().split())
        if not goal_words:
            return []
        overlap = len(goal_words & output_words) / len(goal_words)
        if overlap < 0.2 and len(output) > 100:
            return [DefectReport(
                type=DefectType.GOAL_DRIFT,
                description=f"Output diverges from original goal (word overlap: {overlap:.0%})",
                severity=0.6,
                iteration=len(self._call_history),
                suggestion="Re-read the original objective and refocus execution",
            )]
        return []

    def _check_tool_misuse(self) -> list[DefectReport]:
        defects = []
        for i, call in enumerate(self._call_history):
            result = call.get("result", "")
            if result.startswith("Error") or result.startswith("ERROR"):
                if i > 0 and self._call_history[i - 1].get("tool") == call["tool"]:
                    defects.append(DefectReport(
                        type=DefectType.TOOL_MISUSE,
                        description=f"Repeated errors with '{call['tool']}': {result[:80]}",
                        severity=0.7,
                        iteration=call["iteration"],
                        suggestion=f"Stop using '{call['tool']}' with current parameters. Read error message carefully.",
                    ))
        return defects

    def _check_capability_gap(self, output: str) -> list[DefectReport]:
        gap_indicators = [
            "i don't have a tool", "cannot directly", "no access to",
            "i'm unable to", "missing capability", "tool not found",
        ]
        defects = []
        if output:
            lower = output.lower()
            for indicator in gap_indicators:
                if indicator in lower:
                    defects.append(DefectReport(
                        type=DefectType.INSUFFICIENT_CAPABILITY,
                        description=f"Agent reported capability gap: '{indicator}'",
                        severity=0.75,
                        iteration=len(self._call_history),
                        suggestion="Trigger Capability Discovery: combine existing tools or request human help",
                    ))
                    break
        return defects

    def _compute_health(self, defects: list[DefectReport]) -> float:
        if not defects:
            return 1.0
        total_penalty = sum(d.severity * 0.15 for d in defects)
        return max(0.0, 1.0 - total_penalty)

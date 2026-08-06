"""Causal Attribution — root cause analysis for task outcomes.

Traces failures back through the execution chain to identify whether
the root cause was planning error, tool misuse, model hallucination,
or context insufficiency.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class RootCause(StrEnum):
    PLANNING_ERROR = "planning_error"
    TOOL_PARAMETER_ERROR = "tool_parameter_error"
    MODEL_HALLUCINATION = "model_hallucination"
    CONTEXT_INSUFFICIENT = "context_insufficient"
    CAPABILITY_GAP = "capability_gap"
    EXTERNAL_FAILURE = "external_failure"
    UNKNOWN = "unknown"


@dataclass
class CausalNode:
    iteration: int
    action: str
    outcome: str
    is_failure_point: bool = False
    evidence: str = ""


@dataclass
class AttributionResult:
    root_cause: RootCause
    confidence: float  # 0.0-1.0
    causal_chain: list[CausalNode]
    recommendation: str
    fix_action: str


class CausalAttribution:
    """Post-execution root cause analysis engine."""

    def __init__(self):
        self._execution_log: list[dict[str, Any]] = []

    def log_event(
        self,
        iteration: int,
        action: str,
        outcome: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._execution_log.append({
            "iteration": iteration,
            "action": action,
            "outcome": outcome,
            "metadata": metadata or {},
        })

    def analyze(
        self,
        task_goal: str,
        final_outcome: str,
        success: bool,
    ) -> AttributionResult:
        """Determine root cause of task outcome."""
        if success:
            return AttributionResult(
                root_cause=RootCause.UNKNOWN,
                confidence=1.0,
                causal_chain=self._build_chain(),
                recommendation="Task succeeded. No corrective action needed.",
                fix_action="Log successful pattern for future reference.",
            )

        return self._analyze_failure(task_goal, final_outcome)

    def _analyze_failure(
        self,
        goal: str,
        outcome: str,
    ) -> AttributionResult:
        chain = self._build_chain()
        error_outcomes = [
            e for e in chain
            if e.outcome.startswith("Error") or "error" in e.outcome.lower()
        ]

        # Check for repeated tool failures
        if error_outcomes:
            tool_counts: dict[str, int] = {}
            for node in error_outcomes:
                tool = node.action.split(":")[0] if ":" in node.action else node.action
                tool_counts[tool] = tool_counts.get(tool, 0) + 1

            for tool, count in tool_counts.items():
                if count >= 2:
                    return AttributionResult(
                        root_cause=RootCause.TOOL_PARAMETER_ERROR,
                        confidence=0.75,
                        causal_chain=chain,
                        recommendation=f"Tool '{tool}' failed {count} times. Parameters are likely wrong.",
                        fix_action=f"Read tool schema for '{tool}' and correct parameter types/names.",
                    )

        # Check for hallucination indicators
        outcome_lower = outcome.lower()
        hallucination_signs = [
            "i believe", "i think", "probably", "likely",
            "it seems", "appears to be", "might be",
        ]
        if any(sign in outcome_lower for sign in hallucination_signs):
            return AttributionResult(
                root_cause=RootCause.MODEL_HALLUCINATION,
                confidence=0.6,
                causal_chain=chain,
                recommendation="Output contains uncertain language. Agent may be guessing.",
                fix_action="Require tool-based verification before claiming results.",
            )

        # Check for capability gap
        if "no tool" in outcome_lower or "cannot" in outcome_lower:
            return AttributionResult(
                root_cause=RootCause.CAPABILITY_GAP,
                confidence=0.8,
                causal_chain=chain,
                recommendation="Agent reported inability to perform required action.",
                fix_action="Trigger Capability Discovery or request human intervention.",
            )

        # Check for context gaps
        if len(self._execution_log) < 3 and not error_outcomes:
            return AttributionResult(
                root_cause=RootCause.CONTEXT_INSUFFICIENT,
                confidence=0.65,
                causal_chain=chain,
                recommendation="Very few actions taken before failure. Agent may lack context.",
                fix_action="Gather more context (read files, list directories) before acting.",
            )

        # Check for planning issues (many steps, no convergence)
        if len(self._execution_log) > 10:
            return AttributionResult(
                root_cause=RootCause.PLANNING_ERROR,
                confidence=0.7,
                causal_chain=chain,
                recommendation=f"Execution took {len(self._execution_log)} steps without success. Plan may be flawed.",
                fix_action="Re-plan from scratch. Consider alternative execution paths.",
            )

        return AttributionResult(
            root_cause=RootCause.EXTERNAL_FAILURE,
            confidence=0.5,
            causal_chain=chain,
            recommendation="Failure pattern does not match known categories.",
            fix_action="Log for manual review. Consider adding new detection patterns.",
        )

    def _build_chain(self) -> list[CausalNode]:
        chain = []
        for entry in self._execution_log:
            is_error = (
                entry["outcome"].startswith("Error")
                or "error" in entry["outcome"].lower()[:50]
            )
            chain.append(CausalNode(
                iteration=entry["iteration"],
                action=entry["action"],
                outcome=entry["outcome"][:200],
                is_failure_point=is_error,
                evidence=entry["metadata"].get("evidence", ""),
            ))
        return chain

    def reset(self) -> None:
        self._execution_log.clear()

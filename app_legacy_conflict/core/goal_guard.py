"""Goal drift detection and auto-correction for agent trajectories.

whether the agent's current trajectory still aligns with the original objective,
and triggers corrective action when drift exceeds a threshold.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CorrectionStrategy(str, Enum):
    RE_STATE_GOAL = "re_state_goal"
    SIMPLIFY_TASK = "simplify_task"
    BREAK_INTO_SUBTASKS = "break_into_subtasks"
    ASK_USER = "ask_user"


@dataclass
class DriftSignal:
    """Single drift signal detected during a step."""

    name: str
    weight: float
    description: str


@dataclass
class DriftResult:
    """Result of a drift check after one agent step."""

    drift_score: float = 0.0
    signals: list[DriftSignal] = field(default_factory=list)
    triggered: bool = False
    strategy: CorrectionStrategy | None = None
    context: dict[str, Any] = field(default_factory=dict)


class GoalGuard:
    """Tracks the original task objective and detects trajectory drift.

    Usage::

        guard = GoalGuard(objective="Build a REST API for users", threshold=0.6)
        result = await guard.check(step_output=content, tool_calls=tc, iteration=i)
        if result.triggered:
            prompt = guard.build_correction_prompt(result)
    """

    # Built-in drift signals with weights (weights are additive toward 1.0)
    DEFAULT_SIGNALS: dict[str, DriftSignal] = {
        "off_topic_response": DriftSignal(
            name="off_topic_response",
            weight=0.30,
            description="Agent response does not reference task objective keywords",
        ),
        "unnecessary_tool_call": DriftSignal(
            name="unnecessary_tool_call",
            weight=0.15,
            description="Tool call does not appear to advance the task",
        ),
        "repeated_failure": DriftSignal(
            name="repeated_failure",
            weight=0.25,
            description="Same tool or action failed multiple times",
        ),
        "excessive_iterations": DriftSignal(
            name="excessive_iterations",
            weight=0.20,
            description="Too many iterations without meaningful progress",
        ),
        "tangential_content": DriftSignal(
            name="tangential_content",
            weight=0.20,
            description="Response content is tangential to the task",
        ),
    }

    # Keyword patterns that signal task abandonment
    _TANGENT_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r"let'?s\s+(talk|chat|discuss)\s+about\s+(something|something\s+else|other)", re.IGNORECASE),
        re.compile(r"by\s+the\s+way", re.IGNORECASE),
        re.compile(r"(actually|instead)\b.*(different|another|other)\s+topic", re.IGNORECASE),
    ]

    def __init__(
        self,
        objective: str,
        threshold: float = 0.6,
        max_iterations: int = 10,
        max_repeated_failures: int = 3,
        max_tangential_tools_ratio: float = 0.5,
    ):
        self.objective = objective
        self.threshold = threshold
        self.max_iterations = max_iterations
        self.max_repeated_failures = max_repeated_failures
        self.max_tangential_tools_ratio = max_tangential_tools_ratio
        self.signals: dict[str, DriftSignal] = dict(self.DEFAULT_SIGNALS)

        # Runtime state
        self._failure_counts: dict[str, int] = {}
        self._tool_call_count: int = 0
        self._successful_tool_count: int = 0
        self._history: list[DriftResult] = []

    @property
    def drift_score(self) -> float:
        """Cumulative drift score from the latest check, 0.0..1.0."""
        return self._history[-1].drift_score if self._history else 0.0

    @property
    def last_result(self) -> DriftResult | None:
        """Most recent drift result."""
        return self._history[-1] if self._history else None

    def _objective_keywords(self) -> list[str]:
        """Extract meaningful keywords from the objective."""
        stop = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                "being", "have", "has", "had", "do", "does", "did", "will",
                "would", "could", "should", "may", "might", "shall", "can",
                "to", "of", "in", "for", "on", "with", "by", "at", "from",
                "as", "into", "through", "during", "before", "after",
                "above", "below", "between", "out", "off", "over", "under",
                "again", "further", "then", "once", "and", "but", "or",
                "nor", "not", "so", "very", "just", "because", "if", "when",
                "while", "that", "this", "these", "those", "it", "its"}
        words = re.findall(r"[a-zA-Z]{3,}", self.objective.lower())
        return [w for w in words if w not in stop]

    def _check_off_topic(self, content: str, tool_calls: list[dict[str, Any]]) -> DriftSignal | None:
        """Check if the response is off-topic relative to the objective."""
        keywords = self._objective_keywords()
        if not keywords:
            return None
        content_lower = content.lower()
        matched = sum(1 for kw in keywords if kw in content_lower)
        coverage = matched / len(keywords)

        # Also check tool call names for relevance
        tool_names = [tc.get("function", {}).get("name", "") for tc in tool_calls]
        tool_names_str = " ".join(tool_names).lower()
        tool_matches = sum(1 for kw in keywords if kw in tool_names_str)

        if coverage == 0 and not tool_matches:
            return self.signals["off_topic_response"]
        if coverage < 0.25 and not tool_matches:
            return self.signals["off_topic_response"]
        return None

    def _check_tangential(self, content: str) -> DriftSignal | None:
        """Check for tangential / off-topic language patterns."""
        for pattern in self._TANGENT_PATTERNS:
            if pattern.search(content):
                return self.signals["tangential_content"]
        return None

    def _check_unnecessary_tool(self, tool_calls: list[dict[str, Any]]) -> DriftSignal | None:
        """Check if tool calls appear unnecessary for the task."""
        self._tool_call_count += len(tool_calls)

        # If a large fraction of calls are read-only or status checks
        # and we have many total calls, flag as potentially unnecessary
        if self._tool_call_count > 10:
            return self.signals["unnecessary_tool_call"]
        return None

    def _check_repeated_failures(self, tool_name: str, error: str | None) -> DriftSignal | None:
        """Track repeated tool failures."""
        if not error:
            self._successful_tool_count += 1
            return None
        self._failure_counts[tool_name] = self._failure_counts.get(tool_name, 0) + 1
        if self._failure_counts[tool_name] >= self.max_repeated_failures:
            return self.signals["repeated_failure"]
        return None

    def _check_excessive_iterations(self, iteration: int) -> DriftSignal | None:
        """Check if we have burned too many iterations."""
        if iteration >= self.max_iterations:
            return self.signals["excessive_iterations"]
        return None

    def _select_strategy(self, signals: list[DriftSignal]) -> CorrectionStrategy:
        """Pick the most appropriate correction strategy for the detected signals."""
        names = {s.name for s in signals}

        if "repeated_failure" in names:
            return CorrectionStrategy.SIMPLIFY_TASK
        if "excessive_iterations" in names:
            return CorrectionStrategy.BREAK_INTO_SUBTASKS
        if "unnecessary_tool_call" in names or "tangential_content" in names:
            return CorrectionStrategy.RE_STATE_GOAL
        if "off_topic_response" in names:
            return CorrectionStrategy.ASK_USER
        return CorrectionStrategy.RE_STATE_GOAL

    async def check(
        self,
        step_output: str = "",
        tool_calls: list[dict[str, Any]] | None = None,
        tool_results: list[Any] | None = None,
        iteration: int = 0,
        error: str | None = None,
    ) -> DriftResult:
        """Evaluate current step for goal drift.

        Args:
            step_output: The agent's text output for this step.
            tool_calls: Tool calls made during this step.
            tool_results: Results returned from tool execution.
            iteration: Current loop iteration number.
            error: Optional error string from this step.

        Returns:
            DriftResult with drift_score, detected signals, and suggested correction.
        """
        tool_calls = tool_calls or []
        detected: list[DriftSignal] = []

        signal = self._check_off_topic(step_output, tool_calls)
        if signal:
            detected.append(signal)

        signal = self._check_tangential(step_output)
        if signal:
            detected.append(signal)

        signal = self._check_unnecessary_tool(tool_calls)
        if signal:
            detected.append(signal)

        # Check failures for each tool result
        if tool_results:
            for tr in tool_results:
                tool_name = getattr(tr, "tool_name", "")
                err = getattr(tr, "error", None) or getattr(tr, "result", None)
                err_str = str(err) if err else ""
                signal = self._check_repeated_failures(tool_name, err_str)
                if signal:
                    detected.append(signal)

        if error:
            signal = self._check_repeated_failures("__step__", error)
            if signal:
                detected.append(signal)

        signal = self._check_excessive_iterations(iteration)
        if signal:
            detected.append(signal)

        # Compute drift score: weighted sum of unique signal types, capped at 1.0
        score = min(1.0, sum(s.weight for s in detected))

        strategy = self._select_strategy(detected) if detected else None
        triggered = score >= self.threshold and bool(detected)

        result = DriftResult(
            drift_score=score,
            signals=detected,
            triggered=triggered,
            strategy=strategy,
            context={
                "iteration": iteration,
                "tool_call_count": self._tool_call_count,
                "failure_counts": dict(self._failure_counts),
            },
        )
        self._history.append(result)

        if triggered:
            logger.warning(
                "goal_guard.drift_detected",
                extra={"drift_score": score, "signals": [s.name for s in detected], "strategy": strategy.value if strategy else None, "objective": self.objective},
            )
        else:
            logger.debug(
                "goal_guard.check",
                extra={"drift_score": score, "signals": [s.name for s in detected], "iteration": iteration},
            )
        return result

    def build_correction_prompt(self, result: DriftResult) -> str:
        """Build a prompt injection that reminds the agent of the goal.

        Returns a string that can be prepended to the next model prompt.
        """
        strategy = result.strategy or CorrectionStrategy.RE_STATE_GOAL
        signals_str = ", ".join(s.name for s in result.signals)

        if strategy == CorrectionStrategy.RE_STATE_GOAL:
            return (
                "[GOAL REMINDER] You are drifting from the original task objective. "
                f"Original objective: {self.objective} "
                f"Detected issues: {signals_str}. "
                "Re-focus on the original objective and proceed."
            )

        if strategy == CorrectionStrategy.SIMPLIFY_TASK:
            return (
                "[GOAL REMINDER] Your current approach is failing repeatedly. "
                f"Original objective: {self.objective} "
                f"Detected issues: {signals_str}. "
                "Simplify your approach. Focus on the core requirement and avoid over-engineering."
            )

        if strategy == CorrectionStrategy.BREAK_INTO_SUBTASKS:
            return (
                "[GOAL REMINDER] You have spent too many iterations without completing the task. "
                f"Original objective: {self.objective} "
                f"Detected issues: {signals_str}. "
                "Break the task into smaller subtasks and complete them one at a time."
            )

        if strategy == CorrectionStrategy.ASK_USER:
            return (
                "[GOAL REMINDER] You are significantly off-track. "
                f"Original objective: {self.objective} "
                f"Detected issues: {signals_str}. "
                "Pause and ask the user for clarification before proceeding further."
            )

        return (
            "[GOAL REMINDER] Stay focused on the original objective: "
            f"{self.objective}. Detected drift signals: {signals_str}."
        )

    def build_replan_prompt(self, completed_steps: list[dict[str, Any]]) -> str:
        """Build a re-planning prompt that asks the model to revise its plan.

        Args:
            completed_steps: Steps already completed in this session.

        Returns:
            A re-planning prompt string.
        """
        steps_summary = "\n".join(
            f"- Step {i+1}: {step.get('action', 'unknown')} -> {step.get('observation', '')[:200]}"
            for i, step in enumerate(completed_steps)
        )
        return (
            "[RE-PLANNING REQUIRED]\n"
            f"Original objective: {self.objective}\n\n"
            "The current plan is not working effectively. "
            "Please revise your plan based on what has been attempted so far.\n\n"
            f"Completed steps so far:\n{steps_summary}\n\n"
            "Provide a new, focused plan that directly serves the original objective. "
            "Be concise and actionable."
        )

    def reset(self, new_objective: str | None = None) -> None:
        """Reset the guard state, optionally with a new objective."""
        self._failure_counts.clear()
        self._tool_call_count = 0
        self._successful_tool_count = 0
        self._history.clear()
        if new_objective:
            self.objective = new_objective

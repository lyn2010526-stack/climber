"""Goal Dynamic Adjuster — runtime goal calibration.

When the original goal is infeasible, proposes viable alternatives
instead of failing or infinite retry.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GoalAssessment:
    feasible: bool
    reason: str
    original_goal: str
    suggested_goal: str = ""
    scope_reduction: float = 0.0  # 0.0-1.0, how much scope was reduced
    prerequisites: list[str] = field(default_factory=list)


@dataclass
class AdjustmentResult:
    adjusted: bool
    original: str
    revised: str
    reason: str
    alternatives: list[str] = field(default_factory=list)


class GoalDynamicAdjuster:
    """Detects infeasible goals and proposes alternatives."""

    def __init__(self) -> None:
        self._adjustment_history: list[AdjustmentResult] = []
        self._max_adjustments = 3

    def assess_feasibility(
        self,
        goal: str,
        available_tools: list[str],
        failed_attempts: int,
        failure_reasons: list[str],
    ) -> GoalAssessment:
        """Assess whether the current goal is still achievable."""
        tool_set = set(available_tools)

        # Check if too many attempts have failed
        if failed_attempts >= 5:
            return GoalAssessment(
                feasible=False,
                reason=f"Goal has failed {failed_attempts} times",
                original_goal=goal,
                suggested_goal=self._propose_smaller_scope(goal),
                scope_reduction=0.5,
            )

        # Check for capability gaps
        capability_gaps = self._detect_capability_gaps(goal, tool_set)
        if capability_gaps:
            return GoalAssessment(
                feasible=False,
                reason=f"Missing capabilities: {', '.join(capability_gaps)}",
                original_goal=goal,
                suggested_goal=self._adapt_for_gaps(goal, capability_gaps, tool_set),
                scope_reduction=0.3,
                prerequisites=capability_gaps,
            )

        # Check for overly broad goals
        scope_score = self._estimate_scope(goal)
        if scope_score > 0.8:
            return GoalAssessment(
                feasible=True,
                reason="Goal is very broad but feasible with decomposition",
                original_goal=goal,
                suggested_goal=self._decompose_goal(goal),
                scope_reduction=0.0,
            )

        return GoalAssessment(
            feasible=True,
            reason="Goal appears feasible",
            original_goal=goal,
        )

    def adjust(
        self,
        goal: str,
        available_tools: list[str],
        failed_attempts: int,
        failure_reasons: list[str],
    ) -> AdjustmentResult:
        """Adjust the goal if needed."""
        if len(self._adjustment_history) >= self._max_adjustments:
            return AdjustmentResult(
                adjusted=False,
                original=goal,
                revised=goal,
                reason="Maximum adjustments reached. Stopping.",
            )

        assessment = self.assess_feasibility(
            goal, available_tools, failed_attempts, failure_reasons
        )

        if assessment.feasible:
            return AdjustmentResult(
                adjusted=False,
                original=goal,
                revised=goal,
                reason=assessment.reason,
            )

        result = AdjustmentResult(
            adjusted=True,
            original=goal,
            revised=assessment.suggested_goal or goal,
            reason=assessment.reason,
            alternatives=self._generate_alternatives(goal, available_tools),
        )
        self._adjustment_history.append(result)
        return result

    def _detect_capability_gaps(
        self,
        goal: str,
        tools: set[str],
    ) -> list[str]:
        """Detect what capabilities are missing for this goal."""
        gaps = []
        goal_lower = goal.lower()

        needs_db = any(kw in goal_lower for kw in ["database", "sql", "query data", "db "])
        has_db = any("database" in t or "sql" in t or "db" in t for t in tools)
        if needs_db and not has_db:
            gaps.append("database_access")

        needs_browser = any(kw in goal_lower for kw in ["screenshot", "scrape", "web page", "browser"])
        has_browser = "browser" in tools
        if needs_browser and not has_browser:
            gaps.append("browser_access")

        needs_api = any(kw in goal_lower for kw in ["api call", "rest api", "graphql", "endpoint"])
        has_api = "web_search" in tools or "http_request" in tools
        if needs_api and not has_api:
            gaps.append("api_access")

        return gaps

    def _propose_smaller_scope(self, goal: str) -> str:
        """Produce a smaller-scope version of the goal."""
        if "," in goal:
            parts = [p.strip() for p in goal.split(",")]
            return parts[0]
        if " and " in goal:
            parts = goal.split(" and ")
            return parts[0].strip()
        words = goal.split()
        if len(words) > 6:
            return " ".join(words[:6])
        return goal

    def _adapt_for_gaps(
        self,
        goal: str,
        gaps: list[str],
        tools: set[str],
    ) -> str:
        """Adapt the goal to work around missing capabilities."""
        if "database_access" in gaps and "run_command" in tools:
            return f"{goal} (using CLI database tools instead of direct DB access)"
        if "browser_access" in gaps and "web_search" in tools:
            return f"{goal} (using web search instead of browser)"
        if "api_access" in gaps and "run_command" in tools:
            return f"{goal} (using curl commands for API access)"
        return goal

    def _estimate_scope(self, goal: str) -> float:
        """Estimate how broad the goal is (0.0-1.0)."""
        score = 0.0
        words = goal.split()
        if len(words) > 20:
            score += 0.3
        if len(words) > 40:
            score += 0.2
        if "," in goal:
            score += 0.2
        if " all " in goal.lower() or " every " in goal.lower():
            score += 0.2
        if " and " in goal.lower():
            score += 0.1 * goal.lower().count(" and ")
        return min(1.0, score)

    def _decompose_goal(self, goal: str) -> str:
        """Suggest a decomposed version."""
        if "," in goal:
            parts = [p.strip() for p in goal.split(",")]
            return f"Focus on first part: {parts[0]}"
        return goal

    def _generate_alternatives(
        self,
        goal: str,
        tools: list[str],
    ) -> list[str]:
        """Generate alternative approaches."""
        alternatives = []
        tool_set = set(tools)

        if "run_command" in tool_set:
            alternatives.append(f"Use CLI commands to achieve: {goal}")
        if "read_file" in tool_set and "write_file" in tool_set:
            alternatives.append(f"Manual file editing approach for: {goal}")
        if "web_search" in tool_set:
            alternatives.append(f"Research-based approach for: {goal}")

        if not alternatives:
            alternatives.append("Break the goal into smaller sub-goals")
            alternatives.append("Request human assistance for unavailable capabilities")

        return alternatives[:3]

    def reset(self) -> None:
        self._adjustment_history.clear()

"""Strategy selector — automatic reasoning mode selection.

Selects the best strategy based on task characteristics.
 Falls back to TreeOfThought (most general) when no specific match.
"""

from __future__ import annotations

from app.core.reasoning.base import ReasoningMode, ReasoningRequest


class StrategySelector:
    """Selects reasoning strategy based on task analysis."""

    CODING_KEYWORDS = frozenset({
        "implement", "code", "function", "class", "algorithm",
        "fix", "debug", "refactor", "test", "optimize",
    })

    CREATIVE_KEYWORDS = frozenset({
        "design", "create", "write", "brainstorm", "propose",
        "architecture", "plan", "strategy", "innovate",
    })

    EVAL_KEYWORDS = frozenset({
        "evaluate", "compare", "choose", "review", "assess",
        "recommend", "analyze", "judge", "rank",
    })

    def select(
        self, request: ReasoningRequest, available: dict[ReasoningMode, object]
    ) -> ReasoningMode:
        """Select the best mode for the given request."""
        if request.mode != ReasoningMode.AUTO:
            if request.mode in available:
                return request.mode
            return ReasoningMode.TREE_OF_THOUGHT

        task_lower = request.task.lower()

        if self._matches(task_lower, self.CODING_KEYWORDS):
            if ReasoningMode.DEEP_REFINE in available:
                return ReasoningMode.DEEP_REFINE
            return ReasoningMode.TREE_OF_THOUGHT

        if self._matches(task_lower, self.EVAL_KEYWORDS):
            if ReasoningMode.DEBATE in available:
                return ReasoningMode.DEBATE
            return ReasoningMode.TREE_OF_THOUGHT

        if self._matches(task_lower, self.CREATIVE_KEYWORDS):
            if ReasoningMode.TREE_OF_THOUGHT in available:
                return ReasoningMode.TREE_OF_THOUGHT

        return ReasoningMode.TREE_OF_THOUGHT

    def _matches(self, task: str, keywords: frozenset[str]) -> bool:
        return any(kw in task for kw in keywords)

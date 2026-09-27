"""Resource Orchestrator — adaptive token and context management.

Dynamically controls context compression, MCP lifecycle, loop limits.
Expands resources for complex tasks, throttles for simple ones.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class TaskComplexity(StrEnum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


@dataclass
class ResourceAllocation:
    max_iterations: int
    token_budget: int
    compression_threshold: float  # trigger compression at this ratio
    enable_parallel: bool
    enable_meta_monitoring: bool
    mcp_services: list[str]


@dataclass
class ResourceStatus:
    tokens_used: int
    tokens_remaining: int
    iterations_used: int
    iterations_remaining: int
    compression_triggered: bool
    should_throttle: bool
    should_expand: bool


class ResourceOrchestrator:
    """Adaptive resource management based on task complexity."""

    def __init__(self, default_budget: int = 8000):
        self._default_budget = default_budget
        self._tokens_used = 0
        self._iterations_used = 0
        self._allocation: ResourceAllocation | None = None
        self._complexity = TaskComplexity.MODERATE

    def assess_complexity(self, goal: str, available_tools: list[str]) -> TaskComplexity:
        """Heuristic complexity assessment."""
        score = 0
        goal_lower = goal.lower()

        # Length-based
        if len(goal) > 200:
            score += 2
        elif len(goal) > 80:
            score += 1

        # Keyword-based
        complex_keywords = [
            "refactor", "architecture", "implement", "design",
            "migrate", "optimize", "debug", "full", "complete",
            "multiple", "all", "entire",
        ]
        for kw in complex_keywords:
            if kw in goal_lower:
                score += 1

        # Tool diversity
        if len(available_tools) > 10:
            score += 1

        # Step indicators
        step_indicators = goal.count(",") + goal.count(" and ") + goal.count(";")
        if step_indicators >= 3:
            score += 2
        elif step_indicators >= 1:
            score += 1

        if score >= 5:
            return TaskComplexity.COMPLEX
        if score >= 2:
            return TaskComplexity.MODERATE
        return TaskComplexity.SIMPLE

    def allocate(
        self,
        goal: str,
        available_tools: list[str],
        complexity: TaskComplexity | None = None,
    ) -> ResourceAllocation:
        """Allocate resources based on complexity."""
        if complexity is None:
            complexity = self.assess_complexity(goal, available_tools)
        self._complexity = complexity

        configs = {
            TaskComplexity.SIMPLE: ResourceAllocation(
                max_iterations=5,
                token_budget=self._default_budget // 2,
                compression_threshold=0.8,
                enable_parallel=False,
                enable_meta_monitoring=False,
                mcp_services=["sqlite_state"],
            ),
            TaskComplexity.MODERATE: ResourceAllocation(
                max_iterations=10,
                token_budget=self._default_budget,
                compression_threshold=0.7,
                enable_parallel=True,
                enable_meta_monitoring=True,
                mcp_services=["sqlite_state", "context_compression"],
            ),
            TaskComplexity.COMPLEX: ResourceAllocation(
                max_iterations=20,
                token_budget=self._default_budget * 2,
                compression_threshold=0.6,
                enable_parallel=True,
                enable_meta_monitoring=True,
                mcp_services=["sqlite_state", "context_compression", "trajectory_storage"],
            ),
        }

        self._allocation = configs[complexity]
        self._tokens_used = 0
        self._iterations_used = 0
        return self._allocation

    def record_usage(self, tokens: int) -> None:
        self._tokens_used += tokens
        self._iterations_used += 1

    def get_status(self) -> ResourceStatus:
        if not self._allocation:
            return ResourceStatus(0, 0, 0, 0, False, False, False)

        token_ratio = self._tokens_used / max(self._allocation.token_budget, 1)
        iter_ratio = self._iterations_used / max(self._allocation.max_iterations, 1)

        return ResourceStatus(
            tokens_used=self._tokens_used,
            tokens_remaining=max(0, self._allocation.token_budget - self._tokens_used),
            iterations_used=self._iterations_used,
            iterations_remaining=max(0, self._allocation.max_iterations - self._iterations_used),
            compression_triggered=token_ratio >= self._allocation.compression_threshold,
            should_throttle=token_ratio > 0.85 or iter_ratio > 0.85,
            should_expand=token_ratio < 0.3 and iter_ratio > 0.7,
        )

    def should_compress(self) -> bool:
        status = self.get_status()
        return status.compression_triggered

    def should_stop(self) -> bool:
        if not self._allocation:
            return False
        status = self.get_status()
        return (
            status.tokens_remaining <= 0
            or status.iterations_remaining <= 0
        )

    def get_meta_monitoring_config(self) -> dict[str, Any]:
        """Return config for meta-cognition monitoring."""
        if not self._allocation:
            return {"enabled": False}
        return {
            "enabled": self._allocation.enable_meta_monitoring,
            "check_interval": 3 if self._complexity == TaskComplexity.COMPLEX else 5,
            "defect_threshold": 0.7 if self._complexity == TaskComplexity.SIMPLE else 0.5,
        }

    def reset(self) -> None:
        self._tokens_used = 0
        self._iterations_used = 0
        self._allocation = None
        self._complexity = TaskComplexity.MODERATE

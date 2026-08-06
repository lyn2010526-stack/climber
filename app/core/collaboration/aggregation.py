"""Multi-Agent Result Aggregation.

Provides result collection, consensus evaluation, divergence detection,
and configurable aggregation strategies.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class AggregationStrategy(StrEnum):
    MAJORITY_VOTE = "majority_vote"
    WEIGHTED_AVERAGE = "weighted_average"
    BEST_CONFIDENCE = "best_confidence"


@dataclass
class AgentResult:
    """Result from a single agent for a task."""

    agent_id: str = ""
    task_id: str = ""
    result: Any = None
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "result": self.result,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class AggregationResult:
    """Result of aggregating multiple agent results."""

    task_id: str = ""
    consensus_reached: bool = False
    consensus_value: Any = None
    strategy: AggregationStrategy = AggregationStrategy.BEST_CONFIDENCE
    results: list[AgentResult] = field(default_factory=list)
    divergence_detected: bool = False
    divergent_agents: list[str] = field(default_factory=list)
    aggregation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "aggregation_id": self.aggregation_id,
            "task_id": self.task_id,
            "consensus_reached": self.consensus_reached,
            "consensus_value": self.consensus_value,
            "strategy": self.strategy.value,
            "result_count": len(self.results),
            "divergence_detected": self.divergence_detected,
            "divergent_agents": self.divergent_agents,
            "timestamp": self.timestamp,
        }


class ResultAggregator:
    """Aggregates results from multiple agents with configurable strategies."""

    def __init__(
        self,
        *,
        consensus_threshold: float = 0.6,
        default_strategy: AggregationStrategy = AggregationStrategy.BEST_CONFIDENCE,
    ) -> None:
        self._consensus_threshold = consensus_threshold
        self._default_strategy = default_strategy
        self._results: dict[str, list[AgentResult]] = {}
        self._aggregation_history: list[AggregationResult] = []

    def add_result(self, result: AgentResult) -> None:
        """Add an agent result for aggregation."""
        if result.task_id not in self._results:
            self._results[result.task_id] = []
        self._results[result.task_id].append(result)

    def get_results(self, task_id: str) -> list[AgentResult]:
        """Get all results for a task."""
        return list(self._results.get(task_id, []))

    def get_consensus(self, task_id: str) -> AggregationResult:
        """Get consensus result using majority vote strategy."""
        return self.aggregate(task_id, strategy=AggregationStrategy.MAJORITY_VOTE)

    def get_divergence(self, task_id: str) -> list[AgentResult]:
        """Get results that diverge from the consensus."""
        results = self._results.get(task_id, [])
        if len(results) < 2:
            return []
        consensus = self.get_consensus(task_id)
        if not consensus.consensus_reached:
            return list(results)
        return [
            r for r in results
            if r.agent_id in consensus.divergent_agents
        ]

    def get_weighted_result(self, task_id: str) -> AggregationResult:
        """Get result using weighted average strategy."""
        return self.aggregate(task_id, strategy=AggregationStrategy.WEIGHTED_AVERAGE)

    def aggregate(
        self,
        task_id: str,
        strategy: AggregationStrategy | None = None,
    ) -> AggregationResult:
        """Aggregate results for a task using the specified strategy."""
        results = self._results.get(task_id, [])
        strat = strategy or self._default_strategy

        if not results:
            return AggregationResult(
                task_id=task_id,
                consensus_reached=False,
                strategy=strat,
            )

        if strat == AggregationStrategy.MAJORITY_VOTE:
            agg_result = self._majority_vote(task_id, results)
        elif strat == AggregationStrategy.WEIGHTED_AVERAGE:
            agg_result = self._weighted_average(task_id, results)
        elif strat == AggregationStrategy.BEST_CONFIDENCE:
            agg_result = self._best_confidence(task_id, results)
        else:
            agg_result = self._best_confidence(task_id, results)

        self._aggregation_history.append(agg_result)
        return agg_result

    def _majority_vote(
        self,
        task_id: str,
        results: list[AgentResult],
    ) -> AggregationResult:
        """Majority vote: pick the result with most agreement."""
        groups: dict[str, list[AgentResult]] = {}
        for r in results:
            key = str(r.result)
            if key not in groups:
                groups[key] = []
            groups[key].append(r)

        if not groups:
            return AggregationResult(
                task_id=task_id,
                consensus_reached=False,
                strategy=AggregationStrategy.MAJORITY_VOTE,
                results=results,
            )

        largest_key = max(groups, key=lambda k: len(groups[k]))
        largest_group = groups[largest_key]
        agreement_ratio = len(largest_group) / len(results)
        consensus_reached = agreement_ratio >= self._consensus_threshold

        consensus_agents = {r.agent_id for r in largest_group}
        divergent = [r.agent_id for r in results if r.agent_id not in consensus_agents]

        return AggregationResult(
            task_id=task_id,
            consensus_reached=consensus_reached,
            consensus_value=largest_group[0].result,
            strategy=AggregationStrategy.MAJORITY_VOTE,
            results=results,
            divergence_detected=len(divergent) > 0,
            divergent_agents=divergent,
        )

    def _weighted_average(
        self,
        task_id: str,
        results: list[AgentResult],
    ) -> AggregationResult:
        """Weighted average: combine numeric results by confidence weight."""
        numeric_results = [
            (r, r.confidence) for r in results
            if isinstance(r.result, (int, float))
        ]

        if not numeric_results:
            return self._best_confidence(task_id, results)

        total_weight = sum(w for _, w in numeric_results)
        if total_weight == 0:
            return self._best_confidence(task_id, results)

        weighted_sum = sum(r.result * w for r, w in numeric_results)
        avg_value = weighted_sum / total_weight

        max_confidence = max(r.confidence for r in results)
        consensus_reached = max_confidence >= self._consensus_threshold

        return AggregationResult(
            task_id=task_id,
            consensus_reached=consensus_reached,
            consensus_value=avg_value,
            strategy=AggregationStrategy.WEIGHTED_AVERAGE,
            results=results,
            divergence_detected=not consensus_reached,
        )

    def _best_confidence(
        self,
        task_id: str,
        results: list[AgentResult],
    ) -> AggregationResult:
        """Best confidence: pick the result with highest confidence."""
        best = max(results, key=lambda r: r.confidence)
        consensus_reached = best.confidence >= self._consensus_threshold

        divergent = [
            r.agent_id for r in results
            if r.agent_id != best.agent_id and r.result != best.result
        ]

        return AggregationResult(
            task_id=task_id,
            consensus_reached=consensus_reached,
            consensus_value=best.result,
            strategy=AggregationStrategy.BEST_CONFIDENCE,
            results=results,
            divergence_detected=len(divergent) > 0,
            divergent_agents=divergent,
        )

    def get_history(self, task_id: str | None = None) -> list[AggregationResult]:
        """Get aggregation history, optionally filtered by task."""
        if task_id:
            return [r for r in self._aggregation_history if r.task_id == task_id]
        return list(self._aggregation_history)

    def clear_task(self, task_id: str) -> None:
        """Clear results for a task."""
        self._results.pop(task_id, None)

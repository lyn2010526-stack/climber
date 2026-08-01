"""Result aggregation and cross-validation for multi-agent execution.

When multiple agents work on related tasks, this module merges their results
and flags discrepancies for human review.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class AgentResult:
    """Result from a single agent execution."""

    agent_name: str
    task_description: str
    output: str
    success: bool = True
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregatedResult:
    """Merged result from multiple agents."""

    task: str
    consensus: str
    agent_results: list[AgentResult]
    discrepancies: list[str]
    confidence: float  # 0.0 - 1.0
    needs_review: bool


class ResultAggregator:
    """Aggregates results from multiple agents and detects discrepancies."""

    def __init__(self, *, discrepancy_threshold: float = 0.3) -> None:
        self._discrepancy_threshold = discrepancy_threshold

    def aggregate(
        self,
        task: str,
        results: list[AgentResult],
    ) -> AggregatedResult:
        """Merge results and detect disagreements."""
        if not results:
            return AggregatedResult(
                task=task,
                consensus="",
                agent_results=[],
                discrepancies=[],
                confidence=0.0,
                needs_review=True,
            )

        if len(results) == 1:
            r = results[0]
            return AggregatedResult(
                task=task,
                consensus=r.output,
                agent_results=results,
                discrepancies=[],
                confidence=1.0 if r.success else 0.0,
                needs_review=not r.success,
            )

        discrepancies = self._find_discrepancies(results)
        confidence = self._compute_confidence(results, discrepancies)
        consensus = self._build_consensus(results)
        needs_review = (
            len(discrepancies) > 0 or confidence < (1.0 - self._discrepancy_threshold)
        )

        if needs_review:
            logger.info(
                "result_review_needed",
                task=task[:60],
                discrepancies=len(discrepancies),
                confidence=round(confidence, 2),
            )

        return AggregatedResult(
            task=task,
            consensus=consensus,
            agent_results=results,
            discrepancies=discrepancies,
            confidence=confidence,
            needs_review=needs_review,
        )

    def _find_discrepancies(self, results: list[AgentResult]) -> list[str]:
        """Compare agent outputs and flag differences."""
        discrepancies: list[str] = []
        successful = [r for r in results if r.success]

        if not successful:
            return ["All agents failed"]

        statuses = {r.agent_name: r.success for r in results}
        if all(statuses.values()):
            pass  # all succeeded
        elif any(statuses.values()):
            failed = [name for name, ok in statuses.items() if not ok]
            discrepancies.append(f"Partial failure: {', '.join(failed)} reported errors")

        outputs = {r.agent_name: r.output.strip() for r in successful if r.output.strip()}
        if len(outputs) >= 2:
            unique_outputs = set(outputs.values())
            if len(unique_outputs) > 1:
                summary_diffs = self._summarize_differences(outputs)
                discrepancies.append(
                    f"Output divergence: {summary_diffs}"
                )

        return discrepancies

    def _summarize_differences(self, outputs: dict[str, str]) -> str:
        """Create a brief summary of how outputs differ."""
        summaries = []
        for name, output in outputs.items():
            first_line = output.split("\n")[0][:60]
            summaries.append(f"{name}: '{first_line}...'")
        return " | ".join(summaries)

    def _compute_confidence(
        self, results: list[AgentResult], discrepancies: list[str],
    ) -> float:
        """Compute overall confidence from agent agreement."""
        if not results:
            return 0.0
        success_rate = sum(1 for r in results if r.success) / len(results)
        if not discrepancies:
            return success_rate
        penalty = min(len(discrepancies) * 0.2, 0.6)
        return max(0.0, success_rate - penalty)

    def _build_consensus(self, results: list[AgentResult]) -> str:
        """Build a single consensus output from multiple results."""
        successful = [r for r in results if r.success and r.output.strip()]
        if not successful:
            failed = [r for r in results if not r.success]
            if failed:
                return f"[Execution failed: {failed[0].error}]"
            return "[No output]"

        if len(successful) == 1:
            return successful[0].output

        parts = [f"## Consolidated Output ({len(successful)} agents)"]
        for r in successful:
            parts.append(f"\n### {r.agent_name}\n{r.output}")
        return "\n".join(parts)


_aggregator: ResultAggregator | None = None


def get_aggregator() -> ResultAggregator:
    global _aggregator
    if _aggregator is None:
        _aggregator = ResultAggregator()
    return _aggregator

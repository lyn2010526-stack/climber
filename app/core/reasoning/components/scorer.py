"""Candidate scorer — multi-dimensional scoring and selection."""

from __future__ import annotations

from typing import Any

import structlog

from app.core.reasoning.base import (
    Candidate,
    CoverageReport,
    CritiqueResult,
)

logger = structlog.get_logger()

_DIMENSIONS = ("correctness", "completeness", "clarity", "safety", "actionability")

_DEFAULT_WEIGHTS: dict[str, float] = {
    "correctness": 0.30,
    "completeness": 0.25,
    "clarity": 0.15,
    "safety": 0.15,
    "actionability": 0.15,
}

_CRITIQUE_BONUS = 0.05
_CRITICAL_PENALTY = 0.15
_MAJOR_PENALTY = 0.08
_COVERAGE_WEIGHT = 0.15


class CandidateScorer:
    """Scores candidates across multiple dimensions and selects the best."""

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = weights or _DEFAULT_WEIGHTS
        self._validate_weights()

    def _validate_weights(self) -> None:
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.01:
            factor = 1.0 / total
            self.weights = {k: v * factor for k, v in self.weights.items()}

    async def score(
        self,
        candidate: Candidate,
        task: str,
        model_adapter: Any,
    ) -> float:
        critique = candidate.critique
        if not critique or not critique.scores:
            logger.debug(
                "No critique scores available, using confidence",
                candidate_id=candidate.id,
            )
            return candidate.confidence

        base_score = self._weighted_score(critique.scores)
        adjusted = self._apply_modifiers(base_score, critique)

        logger.debug(
            "Candidate scored",
            candidate_id=candidate.id,
            base=f"{base_score:.3f}",
            adjusted=f"{adjusted:.3f}",
        )
        return round(adjusted, 4)

    def score_from_critique(self, critique: CritiqueResult) -> float:
        """Compute confidence score directly from a CritiqueResult.

        Used by strategies that need a quick confidence estimate
        without a full model call.
        """
        if not critique or not critique.scores:
            return 0.5
        base = self._weighted_score(critique.scores)
        adjusted = self._apply_modifiers(base, critique)
        return round(adjusted, 4)

    def select_best(
        self,
        candidates: list[Candidate],
        coverage: CoverageReport | None = None,
    ) -> Candidate:
        if not candidates:
            raise ValueError("Cannot select best from empty candidate list")

        if len(candidates) == 1:
            return candidates[0]

        scored: list[tuple[float, Candidate]] = []
        for candidate in candidates:
            score = self._compute_selection_score(candidate, coverage)
            scored.append((score, candidate))

        scored.sort(key=lambda x: x[0], reverse=True)

        best_score, best_candidate = scored[0]
        runner_up_score = scored[1][0] if len(scored) > 1 else 0.0

        if len(scored) > 1 and abs(best_score - runner_up_score) < 0.01:
            best_candidate = self._tie_break(scored)

        logger.info(
            "Best candidate selected",
            candidate_id=best_candidate.id,
            score=f"{best_score:.3f}",
            margin=f"{best_score - runner_up_score:.3f}",
        )
        return best_candidate

    def _compute_selection_score(
        self,
        candidate: Candidate,
        coverage: CoverageReport | None,
    ) -> float:
        critique = candidate.critique
        if not critique or not critique.scores:
            base = candidate.confidence
        else:
            base = self._weighted_score(critique.scores)
            base = self._apply_modifiers(base, critique)

        if coverage is not None:
            base = (1 - _COVERAGE_WEIGHT) * base + _COVERAGE_WEIGHT * coverage.score

        return base

    def _weighted_score(self, scores: dict[str, float]) -> float:
        total = 0.0
        used_weight = 0.0
        for dim in _DIMENSIONS:
            if dim in scores:
                weight = self.weights.get(dim, 0.0)
                normalized = self._normalize_score(scores[dim])
                total += weight * normalized
                used_weight += weight

        if used_weight < 1.0 and used_weight > 0:
            total = total / used_weight

        return min(1.0, max(0.0, total))

    def _apply_modifiers(self, base_score: float, critique: CritiqueResult) -> float:
        adjusted = base_score

        if critique.passed and critique.critical_count == 0:
            adjusted += _CRITIQUE_BONUS

        adjusted -= critique.critical_count * _CRITICAL_PENALTY
        adjusted -= critique.major_count * _MAJOR_PENALTY

        return min(1.0, max(0.0, adjusted))

    def _normalize_score(self, value: float) -> float:
        if value > 1.5:
            return min(1.0, value / 5.0)
        return min(1.0, max(0.0, value))

    def _tie_break(self, scored: list[tuple[float, Candidate]]) -> Candidate:
        best_score = scored[0][0]
        contenders = [c for s, c in scored if abs(s - best_score) < 0.01]

        if len(contenders) == 1:
            return contenders[0]

        contenders.sort(key=lambda c: self._tie_break_key(c), reverse=True)
        return contenders[0]

    def _tie_break_key(self, candidate: Candidate) -> tuple[float, float, float]:
        critique = candidate.critique
        if critique:
            no_critique_passed = 1.0 if critique.passed else 0.0
            issue_penalty = -(
                critique.critical_count * 10
                + critique.major_count * 3
                + critique.major_count
            )
            return (no_critique_passed, issue_penalty, candidate.confidence)
        return (0.0, 0.0, candidate.confidence)

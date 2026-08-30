"""Scorer abstraction for the evaluation framework (Mastra-style).

A scorer grades a single agent output against expectations and returns a
normalized 0.0-1.0 score plus a human-readable reason. Scorers are
composable and injectable: the LLM judge takes a judge_fn callable so
tests and production can plug in any model gateway.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass
class ScorerResult:
    score: float  # 0.0 - 1.0
    passed: bool
    reason: str = ""


@runtime_checkable
class Scorer(Protocol):
    """Grades one agent output. Implementations must be side-effect free."""

    name: str

    async def score(self, *, input: str, output: str, expected: dict[str, Any]) -> ScorerResult:
        ...


class ExactMatchScorer:
    name = "exact_match"

    async def score(self, *, input: str, output: str, expected: dict[str, Any]) -> ScorerResult:
        want = str(expected.get("output", "")).strip()
        got = output.strip()
        passed = got == want
        return ScorerResult(
            score=1.0 if passed else 0.0,
            passed=passed,
            reason="exact match" if passed else f"expected {want!r}, got {got[:120]!r}",
        )


class ContainsScorer:
    name = "contains"

    async def score(self, *, input: str, output: str, expected: dict[str, Any]) -> ScorerResult:
        needles = [str(n) for n in expected.get("contains", [])]
        missing = [n for n in needles if n not in output]
        passed = not missing
        return ScorerResult(
            score=1.0 - (len(missing) / len(needles)) if needles else 1.0,
            passed=passed,
            reason="all substrings present" if passed else f"missing: {', '.join(missing)}",
        )


class RegexScorer:
    name = "regex"

    async def score(self, *, input: str, output: str, expected: dict[str, Any]) -> ScorerResult:
        pattern = str(expected.get("regex", ""))
        try:
            passed = bool(re.search(pattern, output))
        except re.error as e:
            return ScorerResult(score=0.0, passed=False, reason=f"invalid regex: {e}")
        return ScorerResult(
            score=1.0 if passed else 0.0,
            passed=passed,
            reason=f"matched /{pattern}/" if passed else f"no match for /{pattern}/",
        )


class LLMJudgeScorer:
    """LLM-as-judge with an injectable judge function.

    judge_fn receives a grading prompt and returns a 0.0-1.0 quality score.
    Injecting the callable keeps the scorer testable and provider-agnostic.
    """

    name = "llm_judge"

    def __init__(
        self,
        judge_fn: Callable[[str], Awaitable[float]],
        pass_threshold: float = 0.7,
    ):
        self._judge_fn = judge_fn
        self._pass_threshold = pass_threshold

    async def score(self, *, input: str, output: str, expected: dict[str, Any]) -> ScorerResult:
        prompt = (
            "Grade the agent output from 0.0 to 1.0 for correctness and completeness.\n"
            f"Input: {input}\n"
            f"Expected: {expected.get('output', expected.get('contains', ''))}\n"
            f"Actual output: {output}\n"
            "Reply with a single number."
        )
        try:
            raw = await self._judge_fn(prompt)
            score = max(0.0, min(1.0, float(raw)))
        except (ValueError, TypeError) as e:
            return ScorerResult(score=0.0, passed=False, reason=f"judge error: {e}")
        return ScorerResult(
            score=score,
            passed=score >= self._pass_threshold,
            reason=f"judge score {score:.2f} (threshold {self._pass_threshold})",
        )


_SCORERS: dict[str, type] = {
    ExactMatchScorer.name: ExactMatchScorer,
    ContainsScorer.name: ContainsScorer,
    RegexScorer.name: RegexScorer,
}


def get_scorer(name: str) -> Scorer:
    """Look up a built-in scorer by name."""
    if name not in _SCORERS:
        raise KeyError(f"Unknown scorer: {name!r}. Available: {sorted(_SCORERS)}")
    return _SCORERS[name]()

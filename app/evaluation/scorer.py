"""Scorer layer for evaluation (research-100 P1).

Scorers turn a SolverResult into a graded score for one task. Only
deterministic assertions are used here; no model-graded scores are invented.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from app.headless.runner import ExitStatus

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .task import EvalTask


class Score:
    __slots__ = ("passed", "rationale", "score", "task_id")

    def __init__(self, task_id: str, score: float, passed: bool, rationale: str = "") -> None:
        self.task_id = task_id
        self.score = score
        self.passed = passed
        self.rationale = rationale


class ScoreError(Exception):
    pass


class Scorer(Protocol):
    def score(self, task: EvalTask, result: Any) -> Score:
        ...


class Judge(Protocol):
    def __call__(self, task: EvalTask, output: str) -> tuple[float, str]:
        ...


class HeadlessScorer:
    """Grade a headless run deterministically.

    A run that reached the normal completion status counts as solved. Among
    solved runs, every check satisfied yields 1.0; otherwise the fraction of
    satisfied checks is reported. Unfinished/budget-exhausted runs score zero.
    """

    def __init__(self) -> None:
        self._solved_statuses = (ExitStatus.MODEL_COMPLETED_UNVERIFIED, ExitStatus.SUCCESS)

    @staticmethod
    def _reads_output(result: Any) -> str:
        return getattr(result, "output", "") or ""

    def score(self, task: EvalTask, result: Any) -> Score:
        status = getattr(result, "status", None)
        if status is None:
            raise ScoreError("Result carries no status")
        if status not in self._solved_statuses:
            return Score(task.id, 0.0, False)
        output = self._reads_output(result)
        if not output:
            return Score(task.id, 0.0, False)
        checks = task.checks
        if not checks:
            return Score(task.id, 1.0, True)
        satisfied = 0
        for check in checks:
            if check(output, task.reference):
                satisfied += 1
        return Score(task.id, satisfied / len(checks), satisfied == len(checks))


class ModelGradedScorer:
    """Rubric-based grading via an injected judge. Never fabricates a score.

    An unsolved/failed run scores zero WITHOUT invoking the judge, so grading
    cannot rescue a failed run. The judge's value must be a real float in
    [0, 1]; anything else raises ScoreError rather than being coerced.
    """

    def __init__(self, judge: Judge, threshold: float = 0.5) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ScoreError("threshold must be within [0, 1]")
        self._judge = judge
        self._threshold = threshold
        self._solved_statuses = (ExitStatus.MODEL_COMPLETED_UNVERIFIED, ExitStatus.SUCCESS)

    def score(self, task: EvalTask, result: Any) -> Score:
        status = getattr(result, "status", None)
        if status is None:
            raise ScoreError("Result carries no status")
        if status not in self._solved_statuses:
            return Score(task.id, 0.0, False)
        output = getattr(result, "output", "") or ""
        if not output:
            return Score(task.id, 0.0, False)
        value, rationale = self._judge(task, output)
        if not isinstance(value, float) or not 0.0 <= value <= 1.0:
            raise ScoreError("Judge must return a float within [0, 1]")
        if not isinstance(rationale, str):
            raise ScoreError("Judge rationale must be text")
        return Score(task.id, value, value >= self._threshold, rationale)

    @staticmethod
    def agreement(scores: Sequence[Score], human_passed: Sequence[bool]) -> float:
        """Fraction of runs where the model grade matches the human label.

        Only caller-supplied labels are used; the harness never invents labels.
        Raises ValueError when agreement is undefined (no/mismatched labels).
        """
        if not scores or len(scores) != len(human_passed):
            raise ValueError("Agreement requires one human label per score")
        matches = sum(1 for score, human in zip(scores, human_passed, strict=True) if score.passed == human)
        return matches / len(scores)

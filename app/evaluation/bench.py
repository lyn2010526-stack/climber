"""Benchmark assembly for evaluation (research-100 P1).

A bench runs one task through a solver, grades it with a scorer, and returns an
aggregate report over the run — passing only stores real measured numbers.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .task import EvalTask


@dataclass
class BenchReport:
    task_id: str
    score: float
    passed: bool
    status: int
    output: str
    tokens_used: int
    turns_used: int
    tool_calls_used: int
    reason: str
    seconds_used: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BenchResult:
    """Aggregate over a task: a single scored run plus its report."""

    report: BenchReport


@dataclass
class SuiteReport:
    """Aggregate over many tasks. Every number is measured, never imputed."""

    tasks: list[BenchReport]
    passed: int
    failed: int
    pass_rate: float
    mean_score: float
    total_tokens: int
    total_turns: int
    total_tool_calls: int
    total_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BenchRunner:
    """Assemble solver + scorer around one eval task."""

    def __init__(self, solver, scorer) -> None:
        self.solver = solver
        self.scorer = scorer

    def run(self, task: EvalTask, budget: Any | None = None) -> BenchResult:  # bench run() interface: budget is part of the harness contract
        started = time.monotonic()
        result = self.solver.solve(task)
        score = self.scorer.score(task, result)
        report = BenchReport(
            task_id=task.id,
            score=score.score,
            passed=score.passed,
            status=int(getattr(result, "status", -1)),
            output=getattr(result, "output", "") or "",
            tokens_used=getattr(result, "tokens", 0) or 0,
            turns_used=getattr(result, "turns", 0) or 0,
            tool_calls_used=getattr(result, "tool_calls", 0) or 0,
            reason=getattr(result, "reason", "") or "",
            seconds_used=round(time.monotonic() - started, 6),
        )
        return BenchResult(report=report)


class BenchSuite:
    """Run many eval tasks through one BenchRunner and aggregate measured numbers."""

    def __init__(self, runner: BenchRunner) -> None:
        self.runner = runner

    def run(self, tasks: Iterable[EvalTask]) -> SuiteReport:
        task_list = list(tasks)
        if not task_list:
            raise ValueError("Cannot run an empty suite")
        reports = [self.runner.run(task).report for task in task_list]
        passed = sum(1 for report in reports if report.passed)
        return SuiteReport(
            tasks=reports,
            passed=passed,
            failed=len(reports) - passed,
            pass_rate=passed / len(reports),
            mean_score=sum(report.score for report in reports) / len(reports),
            total_tokens=sum(report.tokens_used for report in reports),
            total_turns=sum(report.turns_used for report in reports),
            total_tool_calls=sum(report.tool_calls_used for report in reports),
            total_seconds=round(sum(report.seconds_used for report in reports), 6),
        )


def write_suite_report(report: SuiteReport, path: str | Path) -> Path:
    """Write measured-only suite results as JSON (no derived score keys)."""
    import json

    target = Path(path)
    target.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return target

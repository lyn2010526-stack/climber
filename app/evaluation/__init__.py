"""Evaluation harness: task definition, solver, and deterministic scorer."""

from .bench import (
    BenchReport,
    BenchResult,
    BenchRunner,
    BenchSuite,
    SuiteReport,
    write_suite_report,
)
from .scorer import HeadlessScorer, ModelGradedScorer, Score, ScoreError
from .solver import HeadlessSolver
from .task import EvalTask, contains, equals_any, file_matches, load_eval_task

__all__ = [
    "BenchReport",
    "BenchResult",
    "BenchRunner",
    "BenchSuite",
    "EvalTask",
    "HeadlessScorer",
    "HeadlessSolver",
    "ModelGradedScorer",
    "Score",
    "ScoreError",
    "SuiteReport",
    "contains",
    "equals_any",
    "file_matches",
    "load_eval_task",
    "write_suite_report",
]

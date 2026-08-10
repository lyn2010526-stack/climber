"""Evaluation framework.

"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EvalTestCase:
    id: str
    input: str
    expected_output: str | None = None
    expected_contains: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalDataset:
    id: str
    name: str
    test_cases: list[EvalTestCase] = field(default_factory=list)


@dataclass
class EvalResult:
    test_id: str
    passed: bool
    actual_output: str
    score: float
    latency_ms: float
    error: str | None = None


@dataclass
class EvalRun:
    id: str
    dataset_id: str
    agent_id: str
    results: list[EvalResult] = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    avg_score: float = 0.0
    avg_latency_ms: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class EvaluationRunner:
    """Run evaluation datasets against agents."""

    def __init__(self):
        self._runs: dict[str, EvalRun] = {}

    async def run_dataset(self, dataset: EvalDataset, agent_runner: Callable) -> EvalRun:
        """Run an evaluation dataset."""
        import time
        import uuid

        run_id = str(uuid.uuid4())
        run = EvalRun(id=run_id, dataset_id=dataset.id, agent_id="")
        results: list[EvalResult] = []

        for test_case in dataset.test_cases:
            start = time.time()
            try:
                output = await agent_runner(test_case.input)
                latency = (time.time() - start) * 1000
                passed = self._check_output(output, test_case)
                score = 1.0 if passed else 0.0
                run.passed += int(passed)
                run.failed += int(not passed)
                results.append(EvalResult(
                    test_id=test_case.id,
                    passed=passed,
                    actual_output=output,
                    score=score,
                    latency_ms=latency,
                ))
            except Exception as e:
                latency = (time.time() - start) * 1000
                run.failed += 1
                results.append(EvalResult(
                    test_id=test_case.id,
                    passed=False,
                    actual_output="",
                    score=0.0,
                    latency_ms=latency,
                    error=str(e),
                ))

        run.results = results
        run.avg_score = sum(r.score for r in results) / len(results) if results else 0.0
        run.avg_latency_ms = sum(r.latency_ms for r in results) / len(results) if results else 0.0
        self._runs[run_id] = run
        logger.info("eval_completed", run_id=run_id, passed=run.passed, failed=run.failed)
        return run

    def _check_output(self, actual: str, test_case: EvalTestCase) -> bool:
        if test_case.expected_output is not None:
            return actual.strip() == test_case.expected_output.strip()
        if test_case.expected_contains:
            return all(exp in actual for exp in test_case.expected_contains)
        return True


evaluation_runner = EvaluationRunner()

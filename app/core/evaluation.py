"""Evaluation framework.

"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


def evaluate_gates(
    *,
    pass_rate: float,
    avg_score: float,
    avg_latency_ms: float = 0.0,
    gates: dict[str, float],
) -> tuple[str, list[str]]:
    """Evaluate CI gates against run metrics.

    Returns (verdict, failures): verdict is "pass" when every configured
    gate holds, otherwise "fail" with one human-readable reason per
    violated gate. Recognized keys: min_pass_rate, min_avg_score,
    max_avg_latency_ms.
    """
    failures: list[str] = []
    checks = [
        ("min_pass_rate", pass_rate, "pass_rate"),
        ("min_avg_score", avg_score, "avg_score"),
    ]
    for gate_key, actual, label in checks:
        threshold = gates.get(gate_key)
        if threshold is not None and actual < threshold:
            failures.append(f"{label} {actual:.3f} below gate {threshold:.3f}")
    max_latency = gates.get("max_avg_latency_ms")
    if max_latency is not None and avg_latency_ms > max_latency:
        failures.append(f"avg_latency_ms {avg_latency_ms:.0f} above gate {max_latency:.0f}")
    return ("fail" if failures else "pass"), failures


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
    reason: str = ""


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
    verdict: str = "pass"  # "pass" | "fail" — CI gate outcome
    gate_failures: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class EvaluationRunner:
    """Run evaluation datasets against agents."""

    def __init__(self):
        self._runs: dict[str, EvalRun] = {}

    async def run_dataset(
        self,
        dataset: EvalDataset,
        agent_runner: Callable,
        scorers: list | None = None,
        gates: dict[str, float] | None = None,
    ) -> EvalRun:
        """Run an evaluation dataset.

        Args:
            scorers: Optional Scorer list applied to every test case.
                     When omitted, legacy exact-match/contains fields decide.
            gates: Optional CI gates, e.g.
                   {"min_pass_rate": 0.9, "min_avg_score": 0.7,
                    "max_avg_latency_ms": 5000}.
                   Sets run.verdict="fail" with run.gate_failures reasons
                   when any gate is violated. No gates -> verdict stays "pass".
        """
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
                if scorers:
                    passed, score, reason = await self._score_with(
                        scorers, test_case, output,
                    )
                else:
                    passed = self._check_output(output, test_case)
                    score = 1.0 if passed else 0.0
                    reason = ""
                run.passed += int(passed)
                run.failed += int(not passed)
                results.append(EvalResult(
                    test_id=test_case.id,
                    passed=passed,
                    actual_output=output,
                    score=score,
                    latency_ms=latency,
                    reason=reason,
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
        if gates:
            self._apply_gates(run, gates)
        self._runs[run_id] = run
        logger.info(
            "eval_completed run_id=%s passed=%d failed=%d verdict=%s",
            run_id, run.passed, run.failed, run.verdict,
        )
        return run

    async def _score_with(self, scorers: list, test_case: EvalTestCase, output: str) -> tuple[bool, float, str]:
        """Run all scorers; a case passes only when every scorer passes."""
        expected = {
            "output": test_case.expected_output,
            "contains": test_case.expected_contains,
            **dict(test_case.metadata),
        }
        results = []
        for scorer in scorers:
            results.append(await scorer.score(input=test_case.input, output=output, expected=expected))
        passed = all(r.passed for r in results)
        score = sum(r.score for r in results) / len(results)
        reason = "; ".join(r.reason for r in results if r.reason)
        return passed, score, reason

    def _apply_gates(self, run: EvalRun, gates: dict[str, float]) -> None:
        total = run.passed + run.failed
        pass_rate = run.passed / total if total else 0.0
        verdict, failures = evaluate_gates(
            pass_rate=pass_rate,
            avg_score=run.avg_score,
            avg_latency_ms=run.avg_latency_ms,
            gates=gates,
        )
        run.verdict = verdict
        run.gate_failures = failures

    def _check_output(self, actual: str, test_case: EvalTestCase) -> bool:
        if test_case.expected_output is not None:
            return actual.strip() == test_case.expected_output.strip()
        if test_case.expected_contains:
            return all(exp in actual for exp in test_case.expected_contains)
        return True


evaluation_runner = EvaluationRunner()

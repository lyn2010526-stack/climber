"""Eval suite aggregation + model-graded scorer tests (research-100 P1 deepening).

Proves aggregation is pure arithmetic over measured numbers and that no score
is fabricated (judge never rescues a failed run; agreement needs real labels).
"""

from __future__ import annotations

import json

import pytest

from app.evaluation import (
    BenchRunner,
    BenchSuite,
    EvalTask,
    HeadlessScorer,
    HeadlessSolver,
    ModelGradedScorer,
    Score,
    ScoreError,
    contains,
    write_suite_report,
)
from app.headless.runner import ExitStatus, RunResult


def _final(content: str) -> list:
    return [
        {
            "usage": {"total_tokens": 10},
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content, "tool_calls": []},
                }
            ],
        }
    ]


def _result(status=ExitStatus.MODEL_COMPLETED_UNVERIFIED, output="42") -> RunResult:
    return RunResult(status, "t", "scripted-fake", turns=1, tool_calls=0, tokens=10, output=output)


def _runner(tmp_path, script) -> BenchRunner:
    return BenchRunner(HeadlessSolver(workspace_root=tmp_path, fake_script=script), HeadlessScorer())


# ─── Suite aggregation ─────────────────────────────────────────────────────


def test_suite_pass_rate_exact(tmp_path) -> None:
    tasks = [EvalTask("hit", "go", checks=[contains("42")]), EvalTask("miss", "go", checks=[contains("nope")])]
    suite = BenchSuite(_runner(tmp_path, _final("42")))
    # Same script for both: "hit" passes, "miss" fails.
    report = suite.run(tasks)
    assert report.passed == 1
    assert report.failed == 1
    assert report.pass_rate == 0.5


def test_suite_totals_equal_sum_of_parts(tmp_path) -> None:
    tasks = [EvalTask(f"t{i}", "go") for i in range(3)]
    report = BenchSuite(_runner(tmp_path, _final("42"))).run(tasks)
    assert report.total_tokens == sum(r.tokens_used for r in report.tasks)
    assert report.total_turns == sum(r.turns_used for r in report.tasks)
    assert report.total_tool_calls == sum(r.tool_calls_used for r in report.tasks)
    assert report.total_seconds == pytest.approx(sum(r.seconds_used for r in report.tasks))


def test_suite_mean_score_is_arithmetic(tmp_path) -> None:
    # Two checks, output satisfies one -> 0.5; a second task satisfies both -> 1.0.
    tasks = [
        EvalTask("a", "go", checks=[contains("42"), contains("absent")]),
        EvalTask("b", "go", checks=[contains("42")]),
    ]
    report = BenchSuite(_runner(tmp_path, _final("42"))).run(tasks)
    assert report.mean_score == pytest.approx(0.75)


def test_empty_suite_raises(tmp_path) -> None:
    with pytest.raises(ValueError):
        BenchSuite(_runner(tmp_path, _final("42"))).run([])


def test_writer_round_trip_no_derived_keys(tmp_path) -> None:
    report = BenchSuite(_runner(tmp_path, _final("42"))).run([EvalTask("t", "go")])
    out = write_suite_report(report, tmp_path / "results.json")
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert set(payload) == set(report.to_dict())
    assert payload["pass_rate"] == 1.0


# ─── Model-graded scorer ───────────────────────────────────────────────────


class _SpyJudge:
    def __init__(self, value=0.9, rationale="ok") -> None:
        self.calls = 0
        self.value = value
        self.rationale = rationale

    def __call__(self, task, output):
        self.calls += 1
        return self.value, self.rationale


def test_model_graded_requires_solved_status() -> None:
    judge = _SpyJudge()
    scorer = ModelGradedScorer(judge)
    score = scorer.score(EvalTask("t", "go"), _result(status=ExitStatus.BUDGET_EXHAUSTED))
    assert score.score == 0.0 and score.passed is False
    assert judge.calls == 0  # judge never invoked for a failed run


def test_model_graded_empty_output_zero() -> None:
    judge = _SpyJudge()
    score = ModelGradedScorer(judge).score(EvalTask("t", "go"), _result(output=""))
    assert score.score == 0.0
    assert judge.calls == 0


def test_model_graded_rejects_out_of_range() -> None:
    with pytest.raises(ScoreError):
        ModelGradedScorer(_SpyJudge(value=1.5)).score(EvalTask("t", "go"), _result())


def test_model_graded_records_rationale() -> None:
    score = ModelGradedScorer(_SpyJudge(value=0.9, rationale="rubric text")).score(EvalTask("t", "go"), _result())
    assert score.score == 0.9
    assert score.passed is True
    assert score.rationale == "rubric text"


def test_model_graded_rejects_non_float() -> None:
    with pytest.raises(ScoreError):
        ModelGradedScorer(_SpyJudge(value="high")).score(EvalTask("t", "go"), _result())


def test_agreement_undefined_without_labels() -> None:
    with pytest.raises(ValueError):
        ModelGradedScorer.agreement([], [])
    with pytest.raises(ValueError):
        ModelGradedScorer.agreement([Score("t", 1.0, True)], [])


def test_agreement_measured_only() -> None:
    scores = [Score("a", 1.0, True), Score("b", 0.0, False), Score("c", 1.0, True)]
    assert ModelGradedScorer.agreement(scores, [True, True, True]) == pytest.approx(2 / 3)

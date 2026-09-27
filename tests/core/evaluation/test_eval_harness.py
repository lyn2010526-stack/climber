"""P1 evaluation harness skeleton tests (research-100 P1).

Covers task definition/checks, solver reuse of the headless runner, and
deterministic grading. No live LLM, no fabricated scores.
"""

from __future__ import annotations

import json

import pytest

from app.evaluation import (
    BenchReport,
    BenchRunner,
    EvalTask,
    HeadlessScorer,
    HeadlessSolver,
    ScoreError,
    contains,
    equals_any,
    file_matches,
    load_eval_task,
)
from app.headless.runner import Budget, ExitStatus, RunResult


def _scripted_final(content: str, id_assistant: int = 1) -> list:
    """Response envelope: a single assistant final answer (no tool calls)."""
    return [
        {
            "usage": {"total_tokens": 12},
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content, "tool_calls": []},
                }
            ],
        }
    ]


def _make_result(status=ExitStatus.MODEL_COMPLETED_UNVERIFIED, output="42", tokens=12, turns=1) -> RunResult:
    return RunResult(status, "t1", "scripted-fake", turns=turns, tool_calls=0, tokens=tokens, output=output)


class TestEvalTask:
    def test_minimal_task(self) -> None:
        task = EvalTask("id1", "answer the question")
        assert task.id == "id1"
        assert task.reference is None
        assert task.checks == []

    def test_rejects_empty_prompt(self) -> None:
        with pytest.raises(ValueError):
            EvalTask("id1", "")


class TestChecks:
    def test_contains_hit_and_miss(self) -> None:
        check = contains("needle")
        assert check("a needle here", None)
        assert not check("nothing", None)

    def test_equals_any(self) -> None:
        check = equals_any(("true", "yes"))
        assert check("true", None)
        assert check(" yes ", None)
        assert not check("no", None)

    def test_file_matches(self, tmp_path) -> None:
        (tmp_path / "out.txt").write_text("hello", encoding="utf-8")
        check = file_matches(tmp_path, "out.txt", "hello")
        assert check("", None)  # output argument is deliberately ignored
        broken = file_matches(tmp_path, "missing.txt", "hello")
        assert not broken("", None)

    def test_file_matches_blocks_escape(self, tmp_path) -> None:
        check = file_matches(tmp_path, "../etc/passwd", "x")
        assert not check("", None)


class TestLoadEvalTask:
    def test_json_task_with_reference(self, tmp_path) -> None:
        p = tmp_path / "t.json"
        p.write_text(json.dumps({"id": "a", "prompt": "p?", "reference": "ans"}), encoding="utf-8")
        task = load_eval_task(str(p))
        assert task.id == "a"
        assert task.reference == "ans"

    def test_rejects_nontext_reference(self, tmp_path) -> None:
        p = tmp_path / "t.json"
        p.write_text(json.dumps({"id": "a", "prompt": "p?", "reference": 123}), encoding="utf-8")
        with pytest.raises(ValueError):
            load_eval_task(str(p))


class TestHeadlessScorer:
    def test_scorer_requires_status(self) -> None:
        scorer = HeadlessScorer()
        task = EvalTask("t", "p")
        with pytest.raises(ScoreError):
            scorer.score(task, object())

    def test_unsupported_status_scores_zero(self) -> None:
        scorer = HeadlessScorer()
        task = EvalTask("t", "p", checks=[contains("never")])
        score = scorer.score(task, _make_result(status=ExitStatus.BUDGET_EXHAUSTED))
        assert score.score == 0.0
        assert not score.passed

    def test_empty_output_scores_zero(self) -> None:
        scorer = HeadlessScorer()
        task = EvalTask("t", "p", checks=[contains("x")])
        score = scorer.score(task, _make_result(output=""))
        assert not score.passed

    def test_checks_satisfied_full_score(self) -> None:
        scorer = HeadlessScorer()
        task = EvalTask("t", "p", checks=[contains("needle"), contains("also")])
        score = scorer.score(task, _make_result(output="needle and also"))
        assert score.score == 1.0
        assert score.passed

    def test_partial_checks_partial_score(self) -> None:
        scorer = HeadlessScorer()
        task = EvalTask("t", "p", checks=[contains("needle"), contains("also")])
        score = scorer.score(task, _make_result(output="needle only"))
        assert score.score == 0.5
        assert not score.passed

    def test_no_checks_is_pass(self) -> None:
        scorer = HeadlessScorer()
        task = EvalTask("t", "p")
        score = scorer.score(task, _make_result(output="anything"))
        assert score.score == 1.0
        assert score.passed


class TestHeadlessSolverAndBench:
    def test_solver_requires_model_source(self, tmp_path) -> None:
        with pytest.raises(ValueError):
            HeadlessSolver(workspace_root=tmp_path).solve(EvalTask("t", "p"))

    def test_end_to_end_pass(self, tmp_path) -> None:
        solver = HeadlessSolver(workspace_root=tmp_path, fake_script=_scripted_final("the answer is 42"))
        scorer = HeadlessScorer()
        task = EvalTask("t-solve", "compute", checks=[contains("42")])
        result = BenchRunner(solver, scorer).run(task)
        assert isinstance(result.report, BenchReport)
        assert result.report.passed
        assert result.report.score == 1.0
        assert result.report.tokens_used == 12
        assert result.report.turns_used == 1

    def test_end_to_end_fail_script_exhausted(self, tmp_path) -> None:
        # An empty script means the fake model errors; the runner reports ERROR.
        solver = HeadlessSolver(workspace_root=tmp_path, fake_script=[])
        scorer = HeadlessScorer()
        task = EvalTask("t-solve", "compute", checks=[contains("42")])
        result = BenchRunner(solver, scorer).run(task)
        assert not result.report.passed
        assert result.report.score == 0.0

    def test_bench_report_exposes_numbers(self, tmp_path) -> None:
        solver = HeadlessSolver(workspace_root=tmp_path, fake_script=_scripted_final("answer"))
        scorer = HeadlessScorer()
        task = EvalTask("t-solve", "compute")
        report = BenchRunner(solver, scorer).run(task).report
        d = report.to_dict()
        assert d["score"] == 1.0
        assert d["tokens_used"] == 12
        assert isinstance(d["turns_used"], int)

    def test_budget_defaults_validate(self) -> None:
        with pytest.raises(ValueError):
            Budget(0)

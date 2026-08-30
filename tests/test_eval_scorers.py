"""Tests for the scorer abstraction and CI gates in the evaluation framework."""

from __future__ import annotations

import pytest

from app.core.eval_scorers import (
    ContainsScorer,
    ExactMatchScorer,
    LLMJudgeScorer,
    RegexScorer,
    get_scorer,
)
from app.core.evaluation import EvalDataset, EvalTestCase, EvaluationRunner


class TestBuiltinScorers:
    @pytest.mark.asyncio
    async def test_exact_match_pass(self):
        scorer = ExactMatchScorer()
        result = await scorer.score(input="q", output="Paris", expected={"output": "Paris"})
        assert result.passed
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_exact_match_fail(self):
        scorer = ExactMatchScorer()
        result = await scorer.score(input="q", output="London", expected={"output": "Paris"})
        assert not result.passed
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_contains_all_required(self):
        scorer = ContainsScorer()
        result = await scorer.score(
            input="q",
            output="The capital is Paris, France",
            expected={"contains": ["Paris", "France"]},
        )
        assert result.passed

    @pytest.mark.asyncio
    async def test_contains_partial_fails(self):
        scorer = ContainsScorer()
        result = await scorer.score(
            input="q",
            output="The capital is Paris",
            expected={"contains": ["Paris", "France"]},
        )
        assert not result.passed
        assert "France" in result.reason

    @pytest.mark.asyncio
    async def test_regex_scorer(self):
        scorer = RegexScorer()
        ok = await scorer.score(input="q", output="answer: 42", expected={"regex": r"\d+"})
        bad = await scorer.score(input="q", output="no digits", expected={"regex": r"\d+"})
        assert ok.passed
        assert not bad.passed

    @pytest.mark.asyncio
    async def test_llm_judge_injected_callable(self):
        async def judge(prompt: str) -> float:
            assert "Paris" in prompt
            return 0.9

        scorer = LLMJudgeScorer(judge_fn=judge, pass_threshold=0.7)
        result = await scorer.score(input="capital?", output="Paris", expected={"output": "Paris"})
        assert result.passed
        assert result.score == pytest.approx(0.9)

    @pytest.mark.asyncio
    async def test_llm_judge_below_threshold(self):
        async def judge(prompt: str) -> float:
            return 0.3

        scorer = LLMJudgeScorer(judge_fn=judge, pass_threshold=0.7)
        result = await scorer.score(input="q", output="wrong", expected={"output": "Paris"})
        assert not result.passed
        assert result.score == pytest.approx(0.3)

    def test_registry_lookup(self):
        assert isinstance(get_scorer("exact_match"), ExactMatchScorer)
        assert isinstance(get_scorer("contains"), ContainsScorer)
        assert isinstance(get_scorer("regex"), RegexScorer)
        with pytest.raises(KeyError):
            get_scorer("nonexistent")


class TestEvaluationRunnerScorers:
    @pytest.mark.asyncio
    async def test_run_with_scorer_records_reason(self):
        dataset = EvalDataset(
            id="d1",
            name="demo",
            test_cases=[
                EvalTestCase(id="t1", input="q1", expected_output="hello"),
            ],
        )

        async def agent(prompt: str) -> str:
            return "hello"

        runner = EvaluationRunner()
        run = await runner.run_dataset(dataset, agent, scorers=[ExactMatchScorer()])
        assert run.passed == 1
        assert run.results[0].reason  # scorer explanation recorded

    @pytest.mark.asyncio
    async def test_legacy_behavior_without_scorers(self):
        dataset = EvalDataset(
            id="d1",
            name="demo",
            test_cases=[EvalTestCase(id="t1", input="q", expected_output="x")],
        )

        async def agent(prompt: str) -> str:
            return "x"

        runner = EvaluationRunner()
        run = await runner.run_dataset(dataset, agent)
        assert run.passed == 1


class TestEvaluationGates:
    @pytest.mark.asyncio
    async def test_gate_pass(self):
        dataset = EvalDataset(
            id="d1",
            name="demo",
            test_cases=[
                EvalTestCase(id="t1", input="q1", expected_output="a"),
                EvalTestCase(id="t2", input="q2", expected_output="b"),
            ],
        )

        async def agent(prompt: str) -> str:
            return {"q1": "a", "q2": "b"}[prompt]

        runner = EvaluationRunner()
        run = await runner.run_dataset(
            dataset, agent, gates={"min_pass_rate": 1.0, "min_avg_score": 0.9},
        )
        assert run.verdict == "pass"
        assert run.gate_failures == []

    @pytest.mark.asyncio
    async def test_gate_fail_records_reasons(self):
        dataset = EvalDataset(
            id="d1",
            name="demo",
            test_cases=[
                EvalTestCase(id="t1", input="q1", expected_output="a"),
                EvalTestCase(id="t2", input="q2", expected_output="b"),
            ],
        )

        async def agent(prompt: str) -> str:
            return "a" if prompt == "q1" else "wrong"

        runner = EvaluationRunner()
        run = await runner.run_dataset(
            dataset, agent, gates={"min_pass_rate": 0.9},
        )
        assert run.verdict == "fail"
        assert any("pass_rate" in f for f in run.gate_failures)

    @pytest.mark.asyncio
    async def test_no_gates_defaults_pass(self):
        dataset = EvalDataset(
            id="d1",
            name="demo",
            test_cases=[EvalTestCase(id="t1", input="q", expected_output="x")],
        )

        async def agent(prompt: str) -> str:
            return "nope"

        runner = EvaluationRunner()
        run = await runner.run_dataset(dataset, agent)
        assert run.verdict == "pass"  # no gates configured -> no CI blocking

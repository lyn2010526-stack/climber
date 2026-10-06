"""Offline contract tests; scripted runners are not real-model validation."""

import asyncio

import pytest

from app.core.evaluation.baseline import compare_to_baseline
from app.core.evaluation.gate import evaluate_proposal
from app.core.evaluation.judges import DeterministicJudge, LLMRubricJudge
from app.core.evaluation.models import EvalScenario, RubricItem, Trajectory
from app.core.evaluation.runner import pass_at_k, pass_hat_k, run_evaluation
from app.core.evaluation.scenarios import builtin_scenarios


def case():
    return EvalScenario(
        "sample",
        "question",
        scenario_id="stable",
        rubric=[RubricItem("correct", "answer", contains_any=["yes", "ok"], essential=True)],
    )


def test_metrics():
    assert pass_at_k(4, 2, 2) == pytest.approx(5 / 6)
    assert pass_hat_k(4, 2, 2) == 0.25
    for args in [(0, 0, 1), (2, -1, 1), (2, 3, 1), (2, 1, 3)]:
        with pytest.raises(ValueError, match="require"):
            pass_at_k(*args)


def test_rubric_any_veto_and_empty_fail_closed():
    judge = DeterministicJudge()
    trajectory = Trajectory("stable", "question", output="ok")
    assert judge.judge(trajectory, case().rubric).passed
    assert not judge.judge(trajectory, []).passed
    assert not judge.judge(
        trajectory, [RubricItem("unverifiable", "semantic", essential=True)]
    ).passed
    assert not judge.judge(
        trajectory, [RubricItem("veto", "bad", not_contains_any=["ok"], veto=True)]
    ).passed
    assert (
        not LLMRubricJudge()
        ._parse_verdicts('{"verdicts":[{"item_id":"correct","passed":"false"}]}', case().rubric)[0]
        .passed
    )


async def test_injected_runner_samples_and_failed_status():
    async def scripted(scenario, index):
        return Trajectory(
            scenario.scenario_id,
            scenario.user_input,
            output="yes",
            status="failed" if index == 0 else "completed",
            tokens_used=7,
            metadata={"execution_source": "scripted_fake"},
        )

    report = await run_evaluation([case()], scripted, k=2, samples=3)
    assert report.total_tokens == 21
    assert report.pass_at_k["aggregate"] == 1
    assert report.pass_hat_k["aggregate"] == 0
    assert len(report.to_dict()["scenarios"][0]["trajectories"]) == 3
    assert not report.scenarios[0].results[0].passed


async def test_timeout_and_budget():
    async def blocked(scenario, index):
        await asyncio.Event().wait()

    report = await run_evaluation([case()], blocked, timeout=0.01)
    assert not report.scenarios[0].passed

    async def costly(scenario, index):
        return Trajectory(scenario.scenario_id, scenario.user_input, output="yes", tokens_used=9)

    report = await run_evaluation([case()], costly, token_budget=8)
    assert not report.scenarios[0].passed
    with pytest.raises(ValueError, match="samples"):
        await run_evaluation([case()], costly, k=0)


async def test_baseline_and_dual_set_gate():
    async def scripted(scenario, index):
        return Trajectory(scenario.scenario_id, scenario.user_input, output="yes")

    report = await run_evaluation([case()], scripted)
    baseline = report.to_baseline()
    assert not compare_to_baseline(report, baseline)["regressed"]
    report.scenarios[0].passed = False
    assert compare_to_baseline(report, baseline)["regressed"]
    result = await evaluate_proposal([case()], [case()], scripted, retention_baseline=baseline)
    assert result["accepted"]
    with pytest.raises(ValueError, match="required"):
        await evaluate_proposal([], [case()], scripted, retention_baseline=baseline)


def test_builtin_ids_are_stable():
    assert [s.scenario_id for s in builtin_scenarios()] == [
        s.scenario_id for s in builtin_scenarios()
    ]

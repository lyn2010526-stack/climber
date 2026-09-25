"""Tests for the LLM planner and LLM review sub-agent."""

from __future__ import annotations

import asyncio
import json

from app.simulation.harness import HarnessOptions, SimulationHarness
from app.simulation.llm_planner import LLMExperimentPlanner, _extract_json
from app.simulation.llm_reviewer import LLMReviewer, _parse_verdict
from app.simulation.models import ExperimentSpec, Verdict
from app.simulation.review import HarnessReviewer, ReviewContext
from app.tools import ToolRegistry


def _fake_tool_def() -> dict:
    return {
        "parameters": {
            "type": "object",
            "properties": {
                "rate": {"type": "number"},
                "temperature": {"type": "number"},
                "epochs": {"type": "integer"},
                "enabled": {"type": "boolean"},
            },
            "required": ["rate"],
        }
    }


def test_extract_json_fenced():
    text = "Here you go:\n```json\n{\"objective\": \"x\", \"sweep\": {}}\n```"
    parsed = _extract_json(text)
    assert parsed == {"objective": "x", "sweep": {}}


def test_extract_json_naked():
    assert _extract_json('{"sweep": {"rate": {"values": [1, 2]}}}') == {
        "sweep": {"rate": {"values": [1, 2]}}
    }
    assert _extract_json("no json here") is None


def test_llm_planner_plans_sweep():
    async def _llm(prompt, system):
        return json.dumps({
            "objective": "maximize throughput",
            "sweep": {
                "rate": {"min": 0.5, "max": 2.0, "steps": 4},
                "temperature": {"values": [1, 5, 10]},
            },
            "base": {"epochs": 10},
        })

    async def go():
        planner = LLMExperimentPlanner(_llm, "simulate", _fake_tool_def())
        return await planner.plan("Find the best rate")

    plan = asyncio.run(go())
    assert plan.total == 4 * 3
    assert plan.objective == "maximize throughput"
    assert all(e.parameters["epochs"] == 10 for e in plan.experiments)
    assert plan.experiments[0].parameters["temperature"] == 1


def test_llm_planner_drops_unknown_params():
    async def _llm(prompt, system):
        return json.dumps({
            "objective": "oops",
            "sweep": {
                "rate": {"values": [1, 2]},
                "evil_param": {"values": [9, 9, 9]},
            },
            "base": {"rm_rf": True},
        })

    async def go():
        planner = LLMExperimentPlanner(_llm, "simulate", _fake_tool_def())
        return await planner.plan("goal")

    plan = asyncio.run(go())
    assert plan.total == 2
    assert "evil_param" not in plan.experiments[0].parameters
    assert "rm_rf" not in plan.experiments[0].parameters


def test_llm_planner_falls_back_on_garbage():
    async def _llm(prompt, system):
        return "I'm sorry, I cannot do that."

    async def go():
        planner = LLMExperimentPlanner(_llm, "simulate", _fake_tool_def())
        return await planner.plan("goal")

    plan = asyncio.run(go())
    # Fallback plan: exactly one candidate, base params only
    assert plan.total == 1
    assert plan.experiments[0].parameters == {}


def test_parse_verdict():
    assert _parse_verdict('{"verdict": "rejected", "reason": "bad"}') == Verdict.REJECTED
    assert _parse_verdict('{"verdict": "accepted"}') == Verdict.ACCEPTED
    assert _parse_verdict('{"verdict": "retry"}') == Verdict.RETRY
    assert _parse_verdict("nonsense") is None


def test_llm_reviewer_verdict():
    async def _llm(prompt, system):
        return '{"verdict": "rejected", "reason": "implausible"}'

    async def go():
        reviewer = HarnessReviewer(extra_review=LLMReviewer(_llm))
        attempt = _attempt("throughput=5.00")
        await reviewer.review(ReviewContext(
            spec=ExperimentSpec(tool_name="simulate", parameters={"rate": 1.0}),
            attempt=attempt,
        ))
        return attempt

    attempt = asyncio.run(go())
    assert attempt.verdict == Verdict.REJECTED
    assert "llm-reviewer" in attempt.reviewer_note


def test_llm_reviewer_retry():
    async def _llm(prompt, system):
        return '{"verdict": "retry", "reason": "inconclusive"}'

    async def go():
        reviewer = HarnessReviewer(extra_review=LLMReviewer(_llm))
        attempt = _attempt("throughput=5.00")
        await reviewer.review(ReviewContext(
            spec=ExperimentSpec(tool_name="simulate", parameters={"rate": 1.0}),
            attempt=attempt,
        ))
        return attempt

    attempt = asyncio.run(go())
    assert attempt.verdict == Verdict.RETRY


def test_llm_reviewer_failure_returns_retry():
    async def _llm(prompt, system):
        raise RuntimeError("llm down")

    async def go():
        reviewer = HarnessReviewer(extra_review=LLMReviewer(_llm))
        attempt = _attempt("throughput=5.00")
        await reviewer.review(ReviewContext(
            spec=ExperimentSpec(tool_name="simulate", parameters={"rate": 1.0}),
            attempt=attempt,
        ))
        return attempt

    attempt = asyncio.run(go())
    assert attempt.verdict == Verdict.RETRY


def test_llm_reviewer_cannot_accept_rejected():
    """LLM accepts, but deterministic probe already rejected → stays rejected."""
    async def _llm(prompt, system):
        return '{"verdict": "accepted", "reason": "looks fine"}'

    async def go():
        reviewer = HarnessReviewer(extra_review=LLMReviewer(_llm))
        attempt = _attempt("diverged, NaN")
        await reviewer.review(ReviewContext(
            spec=ExperimentSpec(tool_name="simulate", parameters={"rate": 9.0}),
            attempt=attempt,
        ))
        return attempt

    attempt = asyncio.run(go())
    assert attempt.verdict == Verdict.REJECTED


def _attempt(output: str):
    from app.simulation.models import ExperimentAttempt
    return ExperimentAttempt(
        round=1, spec_id="s1", tool_name="simulate",
        parameters={"rate": 1.0}, output=output, success=True,
    )


def test_harness_concurrency_dispatches_in_parallel():
    """The semaphore allows concurrent experiments (peak active > 1)."""

    class SlowSim:
        def __init__(self):
            self.active = 0
            self.max_active = 0
            self.total = 0

        async def __call__(self, **kwargs):
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            self.total += 1
            await asyncio.sleep(0.05)
            self.active -= 1
            return f"throughput={kwargs.get('rate', 1.0):.2f}"

    async def go():
        registry = ToolRegistry()
        fake = SlowSim()
        registry.register("simulate", "slow sim", {
            "type": "object",
            "properties": {"rate": {"type": "number"}},
            "required": ["rate"],
        }, fake.__call__)
        harness = SimulationHarness(
            registry,
            options=HarnessOptions(max_rounds=2, concurrency=4),
        )
        from app.simulation.planner import plan_from_schema
        plan = plan_from_schema(
            {"sweep": {"rate": {"values": [1.0, 2.0, 3.0, 4.0]}}},
            tool_name="simulate",
        )
        result = await harness.run_plan(plan, goal="concurrency")
        return result, fake

    result, fake = asyncio.run(go())
    assert result.accepted == 4
    assert fake.total == 4
    assert fake.max_active > 1  # actually ran in parallel
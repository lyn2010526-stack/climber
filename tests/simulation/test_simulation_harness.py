"""Tests for the simulation experiment harness.

Covers the full close-loop: plan generation, dispatch, probe/review
gating, parameter adjust on rejection, ledger persistence, and the
AgentLaboratory-style reviewer loop. A fake tool registry and fake tool
let us exercise the orchestrator without a real simulator.
"""

from __future__ import annotations

import asyncio

import pytest

from app.simulation.adjuster import ParameterAdjuster
from app.simulation.harness import HarnessOptions, SimulationHarness
from app.simulation.ledger import ExperimentLedger
from app.simulation.planner import (
    ExperimentPlan,
    ParamDim,
    plan_from_schema,
)
from app.simulation.probes import (
    detect_divergence,
    detect_error,
    extract_numbers,
    probe_convergence,
)
from app.simulation.review import HarnessReviewer, ParameterPolicy, ReviewContext
from app.simulation.models import ExperimentSpec, Verdict
from app.tools import ToolRegistry


class FakeSimTool:
    """Fake simulation tool whose output depends on a parameter."""

    def __init__(self, behavior: str = "ok"):
        self.behavior = behavior
        self.calls: list[dict] = []

    async def _impl(self, **kwargs) -> str:
        self.calls.append(kwargs)
        if self.behavior == "diverges":
            return "Simulation diverged: flow rate -> NaN"
        if self.behavior == "error":
            return "Error executing mesher: exception at cell 5, traceback"
        if self.behavior == "ok":
            return f"Simulation ok. throughput={float(kwargs.get('rate', 1.0)) * 2:.2f}"

    def make(self):
        return self._impl


def make_registry(behavior: str = "ok") -> tuple[ToolRegistry, FakeSimTool]:
    registry = ToolRegistry()
    fake = FakeSimTool(behavior)
    registry.register("simulate", "Fake simulation tool", {
        "type": "object",
        "properties": {"rate": {"type": "number"}},
        "required": ["rate"],
    }, fake.make())
    return registry, fake


# ── planner / schema tests ──

def test_plan_from_schema_values():
    plan = plan_from_schema(
        {
            "objective": "maximize throughput",
            "sweep": {"rate": {"values": [1, 2, 4, 8]}},
            "base": {"epochs": 10},
        },
        tool_name="simulate",
        max_experiments=64,
    )
    assert plan.total == 4
    assert len(plan.experiments) == 4
    assert plan.experiments[0].parameters["epochs"] == 10
    assert [e.parameters["rate"] for e in plan.experiments] == [1, 2, 4, 8]
    assert plan.objective == "maximize throughput"


def test_plan_from_schema_range():
    plan = plan_from_schema(
        {"sweep": {"rate": {"min": 0.0, "max": 1.0, "steps": 5}}},
        tool_name="simulate",
    )
    assert 1 < plan.total <= 64
    rates = [e.parameters["rate"] for e in plan.experiments]
    assert min(rates) == 0.0
    assert max(rates) == 1.0


def test_plan_respects_cap():
    plan = plan_from_schema(
        {"sweep": {
            "a": {"values": list(range(10))},
            "b": {"values": list(range(10))},
        }},
        tool_name="simulate",
        max_experiments=20,
    )
    assert plan.total <= 20


# ── probes tests ──

def test_extract_numbers():
    assert extract_numbers("price=12.5 and count 3") == [12.5, 3]
    assert extract_numbers("no numbers") == []


def test_detect_divergence():
    assert detect_divergence("simulation diverged, NaN at step 10")
    assert not detect_divergence("all good, converged neatly")


def test_detect_error():
    assert detect_error("Error: exception during traceback")
    assert not detect_error("the value is 42")


def test_probe_convergence_empty():
    r = probe_convergence("")
    assert not r.ok
    assert r.reason == "empty tool output"


def test_probe_convergence_divergence():
    r = probe_convergence("flow -> NaN, blowing up")
    assert not r.ok


def test_probe_convergence_numeric():
    r = probe_convergence("throughput=10.5 coverage=0.95", expect_numbers=True)
    assert r.ok
    assert r.metrics["numbers"] == [10.5, 0.95]


def test_probe_convergence_reads_named_json_metrics():
    r = probe_convergence(
        '{"throughput": 12.5, "yield": 0.98}',
        expect_numbers=True,
        metric_keys=["throughput", "yield"],
    )
    assert r.ok
    assert r.metrics["throughput"] == 12.5
    assert r.metrics["yield"] == 0.98


# ── reviewer tests ──

def test_reviewer_policy_rejects_unknown_param():
    policy = ParameterPolicy(allowed=["rate"])

    async def go():
        reviewer = HarnessReviewer()
        ctx = ReviewContext(
            spec=ExperimentSpec(tool_name="simulate", parameters={"rate": 1.0, "evil": 2}),
            attempt=await make_attempt({"rate": 1.0, "evil": 2}, "ok output"),
            policy=policy,
        )
        await reviewer.review(ctx)
        return ctx

    ctx = asyncio.run(go())
    assert ctx.attempt.verdict == Verdict.REJECTED
    assert "not allowed" in ctx.attempt.reviewer_note


async def make_attempt(params, output, success=True):
    from app.simulation.models import ExperimentAttempt
    return ExperimentAttempt(
        round=1, spec_id="s1", tool_name="simulate",
        parameters=params, output=output, success=success,
    )


def test_reviewer_accepts_good_output():
    async def go():
        reviewer = HarnessReviewer()
        attempt = await make_attempt({"rate": 1.0}, "throughput=2.00")
        await reviewer.review(ReviewContext(
            spec=ExperimentSpec(tool_name="simulate", parameters={"rate": 1.0}),
            attempt=attempt,
        ))
        return attempt
    attempt = asyncio.run(go())
    assert attempt.verdict == Verdict.ACCEPTED


def test_reviewer_rejects_divergent_output():
    async def go():
        reviewer = HarnessReviewer()
        attempt = await make_attempt({"rate": 9.0}, "diverged, NaN")
        await reviewer.review(ReviewContext(
            spec=ExperimentSpec(tool_name="simulate", parameters={"rate": 9.0}),
            attempt=attempt,
        ))
        return attempt
    attempt = asyncio.run(go())
    assert attempt.verdict == Verdict.REJECTED
    assert "probe" in attempt.reviewer_note


# ── adjuster tests ──

def test_adjuster_within_bounds():
    adjuster = ParameterAdjuster(bounds={"rate": (0.0, 10.0)})
    nxt = adjuster.next_parameters(
        ExperimentSpec(tool_name="simulate", parameters={"rate": 8.0}), 1
    )
    assert nxt is not None
    assert 0.0 <= nxt["rate"] <= 10.0
    assert nxt["rate"] < 8.0


def test_adjuster_stops_after_budget():
    adjuster = ParameterAdjuster()
    assert adjuster.next_parameters(
        ExperimentSpec(tool_name="simulate", parameters={"rate": 8.0}), 100
    ) is None


# ── harness end-to-end ──

def test_harness_accepts_good_simulation():
    async def go():
        registry, fake = make_registry("ok")
        harness = SimulationHarness(
            registry,
            options=HarnessOptions(max_rounds=3),
        )
        plan = plan_from_schema(
            {"sweep": {"rate": {"values": [1.0, 2.0]}}},
            tool_name="simulate",
        )
        return await harness.run_plan(plan, goal="tune throughput")

    result = asyncio.run(go())
    assert result.accepted == 2
    assert result.rejected == 0
    assert all(r.accepted_attempt is not None for r in result.reports)


def test_harness_retries_then_gives_up_on_divergence():
    async def go():
        registry, fake = make_registry("diverges")
        adjuster = ParameterAdjuster(bounds={"rate": (0.0, 10.0)})
        harness = SimulationHarness(
            registry,
            adjuster=adjuster,
            options=HarnessOptions(max_rounds=3),
        )
        plan = plan_from_schema(
            {"sweep": {"rate": {"values": [8.0]}}},
            tool_name="simulate",
        )
        result = await harness.run_plan(plan, goal="tune")
        return result, fake

    result, fake = asyncio.run(go())
    assert result.rejected == 1
    report = result.reports[0]
    assert report.rounds_used == 3
    # Each round should dispatch (initial + 2 adjustments)
    assert len(report.attempts) == 3
    # Different parameter values across rounds
    rates = {str(a.parameters.get("rate")) for a in report.attempts}
    assert len(rates) > 1


def test_harness_recovers_when_first_round_errors():
    """A tool that errors (not diverges) should still be re-attempted."""

    class FlakySim:
        def __init__(self):
            self.calls = 0

        async def _impl(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return "Error: exception during traceback"
            return "throughput=99.0"

    async def go():
        registry = ToolRegistry()
        fake = FlakySim()
        registry.register("simulate", "f", {
            "type": "object",
            "properties": {"rate": {"type": "number"}},
            "required": ["rate"],
        }, fake._impl)
        harness = SimulationHarness(
            registry,
            options=HarnessOptions(max_rounds=3),
        )
        plan = plan_from_schema(
            {"sweep": {"rate": {"values": [1.0]}}},
            tool_name="simulate",
        )
        result = await harness.run_plan(plan, goal="recover")
        return result, fake

    result, fake = asyncio.run(go())
    assert result.accepted == 1
    assert fake.calls >= 2


def test_harness_marks_registry_error_as_failed_attempt():
    async def broken(**kwargs):
        raise RuntimeError("solver crashed")

    async def go():
        registry = ToolRegistry()
        registry.register("simulate", "broken", {
            "type": "object",
            "properties": {"rate": {"type": "number"}},
            "required": ["rate"],
        }, broken)
        harness = SimulationHarness(
            registry,
            options=HarnessOptions(max_rounds=1),
        )
        plan = plan_from_schema(
            {"sweep": {"rate": {"values": [1.0]}}},
            tool_name="simulate",
        )
        return await harness.run_plan(plan)

    result = asyncio.run(go())
    attempt = result.reports[0].attempts[0]
    assert not attempt.success
    assert attempt.verdict == Verdict.REJECTED
    assert "tool:" in attempt.reviewer_note


def test_harness_ledger_persists(tmp_path):
    async def go():
        registry, fake = make_registry("ok")
        ledger = ExperimentLedger(tmp_path)
        harness = SimulationHarness(
            registry,
            ledger=ledger,
            options=HarnessOptions(max_rounds=2),
        )
        plan = plan_from_schema(
            {"sweep": {"rate": {"values": [1.0, 2.0]}}},
            tool_name="simulate",
        )
        result = await harness.run_plan(plan, goal="persisted")
        return result, ledger

    result, ledger = asyncio.run(go())
    records = ledger.read_all()
    types = {r["type"] for r in records}
    assert {"goal", "attempt", "report"} <= types
    assert ledger.path.exists()
    # First record is the goal, last records are reports
    assert records[0]["goal"] == "persisted"
    reports = [r for r in records if r["type"] == "report"]
    assert len(reports) == 2
    assert reports[0]["accepted_parameters"]["rate"] == 1.0


def test_harness_policy_blocks_bad_param_before_dispatch():
    """Safe-Lab style: a disallowed param should never reach the tool."""

    async def go():
        registry, fake = make_registry("ok")
        policy = ParameterPolicy(allowed=["rate"])
        harness = SimulationHarness(
            registry,
            reviewer=HarnessReviewer(),
            options=HarnessOptions(max_rounds=2, policy=policy),
        )
        plan = ExperimentPlan(tool_name="simulate", objective="")
        # Craft a spec with an extra parameter not covered by allowlist
        spec = ExperimentSpec(
            tool_name="simulate",
            parameters={"rate": 1.0, "shell": "rm -rf /"},
        )
        plan.experiments = [spec]
        plan.total = 1
        result = await harness.run_plan(plan, goal="blocked")
        return result, fake

    result, fake = asyncio.run(go())
    assert result.rejected == 1
    assert not fake.calls  # tool never called

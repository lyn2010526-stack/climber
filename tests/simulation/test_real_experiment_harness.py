"""End-to-end: the real experiment tool runs through the harness.

Unlike tests that stub tools, this suite drives the genuine
``simulate_experiment`` built-in through ToolRegistry and the
SimulationHarness, including the true divergence→auto-adjust→recovery
cycle on the heat model's CFL boundary.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from app.simulation.harness import HarnessOptions, SimulationHarness
from app.simulation.planner import plan_from_schema
from app.simulation.review import HarnessReviewer, ParameterPolicy
from app.tools import ToolRegistry
from app.tools.builtins import simulate_experiment  # noqa: F401  (registers tool)


def make_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        "simulate_experiment",
        "Run a real numerical experiment (heat/oscillator/logistic)",
        {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "alpha": {"type": "number"},
                "dx": {"type": "number"},
                "dt": {"type": "number"},
                "t_final": {"type": "number"},
            },
            "required": ["model"],
        },
        simulate_experiment,
    )
    return registry


def test_real_tool_registers_and_executes():
    registry = make_registry()
    result = asyncio.run(registry.execute("simulate_experiment", {
        "model": "heat", "alpha": 1e-4, "dx": 0.02, "dt": 1e-4, "t_final": 5.0,
    }))
    parsed = json.loads(result)
    assert parsed["model"] == "heat"
    assert parsed["converged"] is True
    assert parsed["max_temperature"] > 0


def test_harness_real_heat_experiment_converges():
    async def go():
        registry = make_registry()
        policy = ParameterPolicy(allowed=["model", "alpha", "dx", "dt", "t_final", "n_points", "source_temp", "ambient_temp"])
        harness = SimulationHarness(
            registry,
            reviewer=HarnessReviewer(),
            options=HarnessOptions(max_rounds=2, expect_numbers=True, metric_keys=["max_temperature"], policy=policy),
        )
        plan = plan_from_schema(
            {
                "objective": "minimize max temperature",
                "sweep": {"alpha": {"values": [1e-4, 5e-4]}},
                "base": {"model": "heat", "dx": 0.02, "dt": 1e-4, "t_final": 5.0},
            },
            tool_name="simulate_experiment",
        )
        return await harness.run_plan(plan, goal="sweep alpha")

    result = asyncio.run(go())
    assert result.accepted == 2
    for report in result.reports:
        assert report.accepted_attempt is not None
        assert report.accepted_attempt.probe.metrics.get("max_temperature")


def test_harness_divergent_heat_auto_adjusts_and_recovers():
    """The heat model genuinely diverges at large dt (CFL), and the
    harness's ParameterAdjuster nudges it back under the stable bound."""

    async def go():
        registry = make_registry()
        from app.simulation.adjuster import ParameterAdjuster
        from app.simulation.planner import ParamDim

        adjuster = ParameterAdjuster.from_plan_dims(
            [ParamDim(name="dt", values=[0.05], min=0.0001, max=0.05)],
            max_steps=6,
        )
        harness = SimulationHarness(
            registry,
            adjuster=adjuster,
            options=HarnessOptions(max_rounds=6),
        )
        plan = plan_from_schema(
            {
                "objective": "run heat at large dt",
                "sweep": {"dt": {"values": [0.05]}},  # violates CFL for alpha=1e-2, dx=0.02
                "base": {"model": "heat", "alpha": 1e-2, "dx": 0.02, "t_final": 5.0},
            },
            tool_name="simulate_experiment",
        )
        result = await harness.run_plan(plan, goal="recover from divergence")
        report = result.reports[0]
        return result, report

    result, report = asyncio.run(go())
    assert result.rejected == 0
    assert report.accepted_attempt is not None
    # At least one early attempt diverged and a later one converged.
    verdicts = [a.verdict.value for a in report.attempts]
    assert "rejected" in verdicts or any(
        a.probe.reason and "divergence" in a.probe.reason for a in report.attempts
    )
    assert report.rounds_used >= 2

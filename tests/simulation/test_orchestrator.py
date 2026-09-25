"""Tests for the ScienceSimulationAgent (总指挥) orchestrator close-loop."""

from __future__ import annotations

import asyncio
import json

from app.simulation.llm_planner import LLMExperimentPlanner
from app.simulation.orchestrator import (
    AggregateReviewContext,
    OrchestratorOptions,
    ScienceSimulationAgent,
)
from app.simulation.ledger import ExperimentLedger
from app.tools import ToolRegistry


class _FakeMCPClient:
    """A minimal fake MCP client for the register_mcp_tool path."""

    def __init__(self, behavior: str = "ok", name: str = "fake-mcp"):
        self.name = name
        self.behavior = behavior
        self.calls = 0

    async def call_tool(self, tool_name: str, arguments: dict):
        self.calls += 1
        rate = float(arguments.get("rate", 1.0))
        if self.behavior == "diverges" and rate > 5.0:
            return "Simulation diverged: flow rate -> NaN"
        return f"Simulation ok. throughput={rate * 2:.2f}"


def _registry_with_mcp(behavior: str = "ok") -> tuple[ToolRegistry, _FakeMCPClient]:
    registry = ToolRegistry()
    client = _FakeMCPClient(behavior)
    registry.register_mcp_tool(
        "simulate",
        "Runs an external CFD-like simulation and reports throughput",
        {
            "type": "object",
            "properties": {"rate": {"type": "number"}},
            "required": ["rate"],
        },
        client,
        "simulate",
    )
    return registry, client


async def _plan_llm(prompt: str, system: str) -> str:
    return json.dumps({
        "objective": "maximize throughput",
        "sweep": {"rate": {"min": 1.0, "max": 4.0, "steps": 4}},
        "base": {},
    })


def test_orchestrator_runs_plan_and_satisfies():
    """Total command: tool select → plan → harness → aggregate review → done."""

    async def go():
        registry, client = _registry_with_mcp("ok")
        agent = ScienceSimulationAgent(
            registry,
            options=OrchestratorOptions(max_plan_rounds=3, default_tool="simulate"),
            llm_call=_plan_llm,
        )
        result = await agent.run("Find the best rate for max throughput")
        return result, client

    result, client = asyncio.run(go())
    assert result.satisfied is True
    assert result.accepted == 4
    assert result.rejected == 0
    assert len(result.rounds) == 1  # satisfied on first round, no refine
    assert client.calls == 4  # all four sweep candidates dispatched via MCP
    assert result.final_report["satisfied"] is True
    assert "parameters" in result.final_report["best_parameters"]


class _AlwaysDivergentMCP:
    """MCP client whose output always diverges, regardless of parameters."""

    def __init__(self, name: str = "divergent-mcp"):
        self.name = name
        self.calls = 0

    async def call_tool(self, tool_name: str, arguments: dict):
        self.calls += 1
        return "Simulation diverged: flow rate -> NaN"


def test_orchestrator_refines_and_reruns():
    """An always-diverging tool triggers the aggregate-level refine loop."""

    async def go():
        registry = ToolRegistry()
        client = _AlwaysDivergentMCP()
        registry.register_mcp_tool(
            "simulate",
            "Runs an external CFD-like simulation and reports throughput",
            {
                "type": "object",
                "properties": {"rate": {"type": "number"}},
                "required": ["rate"],
            },
            client,
            "simulate",
        )

        async def refined_planner_llm(prompt: str, system: str) -> str:
            return json.dumps({
                "objective": "maximize throughput",
                "sweep": {"rate": {"min": 8.0, "max": 10.0, "steps": 2}},
                "base": {},
            })

        agent = ScienceSimulationAgent(
            registry,
            options=OrchestratorOptions(max_plan_rounds=3, default_tool="simulate"),
            llm_call=refined_planner_llm,
        )
        result = await agent.run("tune to convergence")
        return result, client

    result, client = asyncio.run(go())
    assert result.satisfied is False
    assert len(result.rounds) == 3
    assert result.accepted == 0
    assert result.rejected == 6  # 2 specs x 3 rounds, none accepted
    assert result.final_report["satisfied"] is False
    # 2 dispatch candidates x 3 rounds x up-to-2 attempts each
    assert client.calls >= 6


def test_orchestrator_aggregate_review_can_refine_once():
    """A custom aggregate reviewer can demand one refine round then pass."""

    async def go():
        registry, client = _registry_with_mcp("ok")
        calls = {"n": 0}

        async def reviewer(ctx: AggregateReviewContext) -> tuple[bool, str]:
            calls["n"] += 1
            if calls["n"] == 1:
                return False, "widen the sweep"
            return True, "acceptable now"

        agent = ScienceSimulationAgent(
            registry,
            options=OrchestratorOptions(max_plan_rounds=3, default_tool="simulate"),
            llm_call=_plan_llm,
            global_reviewer=reviewer,
        )
        return await agent.run("tune"), calls

    result, calls = asyncio.run(go())
    assert calls["n"] == 2
    assert len(result.rounds) == 2
    assert result.satisfied is True


def test_orchestrator_default_tool_selection():
    """Without default_tool, the selector picks the simulation tool."""

    async def go():
        registry, client = _registry_with_mcp("ok")
        # Register a second, non-simulation tool to force selection
        async def helper(**kwargs):
            return "helping"

        registry.register("help_me", "A helper", {}, helper)
        agent = ScienceSimulationAgent(
            registry,
            options=OrchestratorOptions(max_plan_rounds=2),
            llm_call=_plan_llm,
        )
        return await agent.run("find best rate")

    result = asyncio.run(go())
    assert result.rounds[0].tool_name == "simulate"
    assert result.satisfied is True


def test_orchestrator_ledger_persists_full_loop(tmp_path):
    async def go():
        registry, client = _registry_with_mcp("ok")
        ledger = ExperimentLedger(tmp_path)
        agent = ScienceSimulationAgent(
            registry,
            options=OrchestratorOptions(max_plan_rounds=2, default_tool="simulate"),
            llm_call=_plan_llm,
            ledger=ledger,
        )
        result = await agent.run("tune throughput")
        return result, ledger

    result, ledger = asyncio.run(go())
    records = ledger.read_all()
    types = {r["type"] for r in records}
    assert {"goal", "plan_round", "final_report"} <= types
    rounds = [r for r in records if r["type"] == "plan_round"]
    assert len(rounds) == 1
    assert rounds[0]["satisfied"] is True
    final = [r for r in records if r["type"] == "final_report"][0]
    assert final["final_report"]["satisfied"] is True
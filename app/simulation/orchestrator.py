"""ScienceSimulationAgent — the "总指挥" orchestrator.

Implements the full prompt: Agent作为总指挥接收自然语言工程需求，拆实验，
调用MCP仿真工具，读取结果，Harness校验合理性，自动迭代参数，完整日志持久化.

Unlike the per-experiment SimulationHarness (which retries a single spec),
this agent runs AgentLaboratory's defining *global* close-loop: it
selects a simulation tool, plans the experiment sweep, runs the harness,
then an aggregate reviewer judges whether the whole round satisfied the
goal; if not, the requirement is refined with reviewer feedback and the
loop re-runs. Every round is recorded in the ledger.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

import structlog

from app.simulation.adjuster import ParameterAdjuster
from app.simulation.harness import HarnessOptions, HarnessRunResult, SimulationHarness
from app.simulation.ledger import ExperimentLedger
from app.simulation.llm_planner import LLMExperimentPlanner
from app.simulation.review import HarnessReviewer

logger = structlog.get_logger()

GlobalReviewFn = Callable[["AggregateReviewContext"], Awaitable[tuple[bool, str]]]
ToolSelectFn = Callable[[str, list[dict[str, Any]]], Awaitable[str]]


@dataclass
class AggregateReviewContext:
    """What the aggregate reviewer sees after one plan round."""
    requirement: str
    tool_name: str
    accepted: int
    rejected: int
    reports: list[dict[str, Any]]
    previous_feedback: str = ""


@dataclass
class PlanRound:
    """One full plan→run→review cycle of the orchestrator."""
    round_number: int = 0
    tool_name: str = ""
    plan_rounds_hint: str = ""
    result: HarnessRunResult | None = None
    satisfied: bool = False
    feedback: str = ""


@dataclass
class OrchestratorOptions:
    """Tuning knobs for the global close-loop."""
    max_plan_rounds: int = 3
    harness_options: HarnessOptions = field(default_factory=HarnessOptions)
    default_tool: str = ""


@dataclass
class OrchestratorResult:
    """Final output of the orchestrator after all plan rounds."""
    requirement: str
    rounds: list[PlanRound] = field(default_factory=list)
    accepted: int = 0
    rejected: int = 0
    satisfied: bool = False
    final_report: dict[str, Any] = field(default_factory=dict)
    ledger_path: str = ""


class ScienceSimulationAgent:
    """总指挥: select tool → plan → harness → aggregate review → refine → repeat."""

    def __init__(
        self,
        tool_registry: Any,
        options: OrchestratorOptions | None = None,
        llm_call=None,
        ledger: ExperimentLedger | None = None,
        global_reviewer: GlobalReviewFn | None = None,
        tool_selector: ToolSelectFn | None = None,
        validate_tool_call=None,
    ):
        self.tool_registry = tool_registry
        self.options = options or OrchestratorOptions()
        self._llm_call = llm_call
        self.ledger = ledger
        self._global_reviewer = global_reviewer or self._default_global_review
        self._tool_selector = tool_selector or self._default_tool_select
        self._validate_tool_call = validate_tool_call

    async def run(self, requirement: str) -> OrchestratorResult:
        result = OrchestratorResult(requirement=requirement)
        if self.ledger is not None:
            self.ledger.record_goal(requirement, {"mode": "orchestrator"})

        feedback = ""
        for round_number in range(1, self.options.max_plan_rounds + 1):
            round_rec = PlanRound(round_number=round_number)

            tool_name = await self._select_tool(requirement)
            round_rec.tool_name = tool_name

            harness = self._make_harness(tool_name)
            llm_planner = self._make_planner(tool_name)
            plan = await llm_planner.plan(requirement)
            round_rec.plan_rounds_hint = f"plan total={plan.total}"

            harness_result = await harness.run_plan(plan, goal=requirement)
            round_rec.result = harness_result

            ctx = AggregateReviewContext(
                requirement=requirement,
                tool_name=tool_name,
                accepted=harness_result.accepted,
                rejected=harness_result.rejected,
                reports=[r.model_dump() for r in harness_result.reports],
                previous_feedback=feedback,
            )
            satisfied, reason = await self._global_reviewer(ctx)
            round_rec.satisfied = satisfied
            round_rec.feedback = reason

            result.rounds.append(round_rec)
            result.accepted += harness_result.accepted
            result.rejected += harness_result.rejected

            if self.ledger is not None:
                self.ledger.record_plan_round(
                    round_number=round_number,
                    tool_name=tool_name,
                    plan_total=plan.total,
                    accepted=harness_result.accepted,
                    rejected=harness_result.rejected,
                    satisfied=satisfied,
                    feedback=reason,
                )

            if satisfied:
                result.satisfied = True
                break
            feedback = reason

        result.final_report = self._build_final_report(result)
        if self.ledger is not None:
            result.ledger_path = str(self.ledger.path)
            self.ledger.record_final_report(result.final_report)
        return result

    async def _select_tool(self, requirement: str) -> str:
        if self.options.default_tool:
            return self.options.default_tool
        available = [
            {
                "name": d.name,
                "description": d.description,
                "type": d.type,
            }
            for d in self.tool_registry.list_tools()
        ]
        if not available:
            raise ValueError("no tools registered")
        try:
            selected = await self._tool_selector(requirement, available)
        except Exception as e:
            logger.warning("tool_select_failed", error=str(e))
            selected = ""
        if not selected or selected not in {d["name"] for d in available}:
            return available[0]["name"]
        return selected

    async def _default_tool_select(self, requirement: str, tools: list[dict[str, Any]]) -> str:
        """Deterministic fallback: pick the first tool whose description
        mentions simulation, else the first tool."""
        for tool in tools:
            desc = (tool.get("description") or "").lower()
            if any(k in desc for k in ("simulate", "simulation", "solver", "compute")):
                return tool["name"]
        return tools[0]["name"]

    async def _default_global_review(self, ctx: AggregateReviewContext) -> tuple[bool, str]:
        """Deterministic aggregate gate: satisfied when at least one
        experiment was accepted and none were rejected."""
        if ctx.accepted > 0 and ctx.rejected == 0:
            return True, "all experiments accepted"
        if ctx.accepted > 0 and ctx.rejected > 0:
            return False, f"only {ctx.accepted} accepted, {ctx.rejected} rejected; narrow the sweep"
        return False, "no experiment accepted; widen the sweep or change the tool"

    def _make_harness(self, tool_name: str) -> SimulationHarness:
        return SimulationHarness(
            self.tool_registry,
            reviewer=HarnessReviewer(),
            adjuster=ParameterAdjuster(),
            ledger=self.ledger,
            options=self.options.harness_options,
            validate_tool_call=self._validate_tool_call,
        )

    def _make_planner(self, tool_name: str) -> LLMExperimentPlanner:
        tool_def = self.tool_registry.get_tool(tool_name) if self.tool_registry else None
        return LLMExperimentPlanner(
            llm_call=self._llm_call or _noop_llm,
            tool_name=tool_name,
            tool_def=tool_def,
        )

    def _build_final_report(self, result: OrchestratorResult) -> dict[str, Any]:
        best: dict[str, Any] = {}
        for round_rec in result.rounds:
            if round_rec.result is None:
                continue
            for report in round_rec.result.reports:
                if report.accepted_attempt is not None:
                    best = {
                        "tool_name": round_rec.tool_name,
                        "parameters": report.accepted_attempt.parameters,
                        "output": report.accepted_attempt.output,
                        "probe_metrics": report.accepted_attempt.probe.metrics,
                    }
                    break
        return {
            "requirement": result.requirement,
            "satisfied": result.satisfied,
            "accepted": result.accepted,
            "rejected": result.rejected,
            "rounds": len(result.rounds),
            "best_parameters": best,
        }


async def _noop_llm(prompt: str, system: str) -> str:
    return "{}"

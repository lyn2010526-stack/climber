"""SimulationHarness — the orchestrating loop.

Implements the "Agent作为总指挥" pattern: receive a natural-language
engineering requirement, decompose it into an experiment sweep, dispatch
each candidate to an external simulation/MCP tool, probe and review the
output, auto-adjust rejected parameters, and persist the entire lifecycle
to a ledger. No simulation solver is implemented here — the harness only
orchestrates tools exposed by ToolRegistry (including MCP servers).
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.core.parallel import ParallelToolExecutor
from app.simulation.adjuster import ParameterAdjuster
from app.simulation.ledger import ExperimentLedger
from app.simulation.models import (
    ExperimentAttempt,
    ExperimentReport,
    ExperimentSpec,
    Verdict,
)
from app.simulation.planner import ExperimentPlan
from app.simulation.review import HarnessReviewer, ReviewContext

logger = structlog.get_logger()


@dataclass
class HarnessOptions:
    """Tuning knobs for the orchestration loop."""
    max_rounds: int = 8
    concurrency: int = 4
    timeout_per_tool: float = 60.0
    expect_numbers: bool = True
    metric_keys: list[str] | None = None
    policy: Any | None = None


@dataclass
class HarnessRunResult:
    """Aggregate result across all experiments in a plan."""
    plan: ExperimentPlan
    reports: list[ExperimentReport] = field(default_factory=list)
    accepted: int = 0
    rejected: int = 0
    ledger_path: str = ""


class SimulationHarness:
    """Close the experiment loop: plan → dispatch → review → adjust → log."""

    def __init__(
        self,
        tool_registry: Any,
        reviewer: HarnessReviewer | None = None,
        adjuster: ParameterAdjuster | None = None,
        ledger: ExperimentLedger | None = None,
        options: HarnessOptions | None = None,
        validate_tool_call=None,
    ):
        self.tool_registry = tool_registry
        self.reviewer = reviewer or HarnessReviewer()
        self.adjuster = adjuster or ParameterAdjuster()
        self.ledger = ledger
        self.options = options or HarnessOptions()
        self._validate_tool_call = validate_tool_call

    async def run_plan(
        self,
        plan: ExperimentPlan,
        goal: str = "",
    ) -> HarnessRunResult:
        """Execute every experiment in a plan, iterating rejected rounds.

        Experiments run concurrently (up to ``options.concurrency``).
        Report/ledger updates are collected after each experiment finishes,
        so ordering across experiments is nondeterministic but every one is
        recorded and counted.
        """
        result = HarnessRunResult(plan=plan)
        if self.ledger is not None:
            self.ledger.record_goal(goal, plan.to_dict())

        if not plan.experiments:
            return result

        # Keep retry adjustments within the same search space as the plan.
        if not self.adjuster.bounds and plan.sweep_dims:
            self.adjuster = ParameterAdjuster.from_plan_dims(
                plan.sweep_dims,
                max_steps=self.options.max_rounds,
            )

        semaphore = asyncio.Semaphore(max(1, self.options.concurrency))

        async def _packaged(spec: ExperimentSpec) -> ExperimentReport:
            async with semaphore:
                return await self._run_experiment(spec)

        reports = await asyncio.gather(
            *[_packaged(spec) for spec in plan.experiments],
        )

        for report in reports:
            result.reports.append(report)
            if report.accepted_attempt is not None:
                result.accepted += 1
            else:
                result.rejected += 1
            if self.ledger is not None:
                self.ledger.record_report(report)

        if self.ledger is not None:
            result.ledger_path = str(self.ledger.path)
        return result

    async def run_requirement(
        self,
        requirement: str,
        tool_name: str,
        schema: dict[str, Any] | None = None,
        goal: str = "",
        llm_planner: Any = None,
    ) -> HarnessRunResult:
        """Plan from a requirement/schema, then run the plan.

        With an ``llm_planner`` (LLMExperimentPlanner) the natural-language
        requirement is converted to a search plan directly; without one,
        the concrete ``schema`` is used as the sweep definition.
        """
        if llm_planner is not None:
            plan = await llm_planner.plan(requirement)
            if not goal:
                goal = requirement
            return await self.run_plan(plan, goal=goal)

        from app.simulation.planner import plan_from_schema

        plan = plan_from_schema(schema or {}, tool_name=tool_name)
        if not goal:
            goal = requirement
        return await self.run_plan(plan, goal=goal)

    async def _run_experiment(self, spec: ExperimentSpec) -> ExperimentReport:
        report = ExperimentReport(spec=spec, max_rounds=self.options.max_rounds)

        for round_number in range(1, self.options.max_rounds + 1):
            parameters = spec.parameters
            if round_number > 1:
                next_params = self.adjuster.next_parameters(spec, round_number - 1)
                if next_params is None:
                    break
                parameters = next_params

            policy = self.options.policy
            if policy is not None:
                ok, reason = policy.validate(parameters)
                if not ok:
                    attempt = ExperimentAttempt(
                        round=round_number,
                        spec_id=spec.id,
                        tool_name=spec.tool_name,
                        parameters=parameters,
                        success=False,
                        reviewer_note=f"policy: {reason}",
                    )
                    attempt.verdict = Verdict.REJECTED
                    report.attempts.append(attempt)
                    if self.ledger is not None:
                        self.ledger.record_attempt(attempt)
                    continue

            attempt = await self._dispatch(spec, round_number, parameters)
            report.attempts.append(attempt)
            if self.ledger is not None:
                self.ledger.record_attempt(attempt)

            ctx = ReviewContext(
                spec=spec,
                attempt=attempt,
                policy=policy,
                expect_numbers=self.options.expect_numbers,
                metric_keys=self.options.metric_keys,
            )
            await self.reviewer.review(ctx)

            if attempt.verdict == Verdict.ACCEPTED:
                report.accepted_attempt = attempt
                report.rounds_used = round_number
                break

        report.rounds_used = report.rounds_used or self.options.max_rounds
        return report

    async def _dispatch(
        self,
        spec: ExperimentSpec,
        round_number: int,
        parameters: dict[str, Any],
    ) -> ExperimentAttempt:
        start = time.time()
        attempt = ExperimentAttempt(
            round=round_number,
            spec_id=spec.id,
            tool_name=spec.tool_name,
            parameters=parameters,
        )
        executor = ParallelToolExecutor(
            self.tool_registry,
            timeout_per_tool=self.options.timeout_per_tool,
            validator=self._validate_tool_call,
        )
        try:
            results = await executor.execute_all([{
                "id": f"{spec.id}-r{round_number}",
                "function": {"name": spec.tool_name, "arguments": parameters},
            }])
            tool_result = results[0]
            attempt.success = tool_result.success
            attempt.output = tool_result.result
            attempt.error = tool_result.error
        except asyncio.CancelledError:
            raise
        except Exception as e:
            attempt.success = False
            attempt.error = str(e)
        finally:
            attempt.duration_ms = (time.time() - start) * 1000
        return attempt

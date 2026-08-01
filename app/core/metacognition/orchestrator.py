"""Metacognition Orchestrator — central coordinator for all meta-cognition capabilities.

Ties together: monitoring, simulation, resource management, causal attribution,
capability discovery, self-refactor, goal adjustment, sub-agent orchestration,
memory pruning, and all MCP plugins into a unified execution loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.metacognition.causal import AttributionResult, CausalAttribution
from app.core.metacognition.goal_adjuster import GoalDynamicAdjuster
from app.core.metacognition.hypothesis import HypothesisSimulator, SimulationResult
from app.core.metacognition.monitor import MetaCognitionMonitor, MonitoringResult
from app.core.metacognition.resource import (
    ResourceAllocation,
    ResourceOrchestrator,
    ResourceStatus,
    TaskComplexity,
)


@dataclass
class ExecutionContext:
    goal: str
    available_tools: list[str]
    token_budget: int = 8000
    complexity: TaskComplexity | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MetacognitionState:
    iteration: int = 0
    monitoring: MonitoringResult | None = None
    simulation: SimulationResult | None = None
    resource_status: ResourceStatus | None = None
    attribution: AttributionResult | None = None
    allocation: ResourceAllocation | None = None
    execution_log: list[dict[str, Any]] = field(default_factory=list)


class MetacognitionOrchestrator:
    """Central coordinator for all meta-cognition capabilities."""

    def __init__(self, token_budget: int = 8000):
        self._monitor = MetaCognitionMonitor()
        self._simulator = HypothesisSimulator(token_budget)
        self._causal = CausalAttribution()
        self._resource = ResourceOrchestrator(token_budget)
        self._goal_adjuster = GoalDynamicAdjuster()
        self._state = MetacognitionState()
        self._enabled = True

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    def initialize(self, ctx: ExecutionContext) -> MetacognitionState:
        """Set up all meta-cognition modules for a new task."""
        self._state = MetacognitionState()

        if not self._enabled:
            return self._state

        # Resource allocation
        allocation = self._resource.allocate(
            ctx.goal, ctx.available_tools, ctx.complexity
        )
        self._state.allocation = allocation

        # Monitor setup
        self._monitor.reset(ctx.goal, allocation.token_budget)

        # Pre-execution simulation
        self._state.simulation = self._simulator.simulate(
            ctx.goal, ctx.available_tools, ctx.metadata
        )

        return self._state

    def pre_action(self, iteration: int) -> dict[str, Any]:
        """Called before each action. Returns guidance for the agent."""
        if not self._enabled:
            return {"proceed": True}

        status = self._resource.get_status()
        guidance: dict[str, Any] = {
            "proceed": True,
            "should_stop": False,
            "should_compress": False,
            "warnings": [],
        }

        if status.should_throttle:
            guidance["warnings"].append(
                "Resource usage high. Prefer simpler actions or conclude."
            )

        if self._resource.should_stop():
            guidance["proceed"] = False
            guidance["should_stop"] = True

        if self._resource.should_compress():
            guidance["should_compress"] = True

        return guidance

    def post_action(
        self,
        iteration: int,
        tool_name: str,
        arguments: dict[str, Any],
        result: str,
        tokens_used: int = 0,
    ) -> dict[str, Any]:
        """Called after each action. Returns monitoring feedback."""
        if not self._enabled:
            return {"continue": True}

        # Record usage
        self._resource.record_usage(tokens_used)
        self._monitor.record_call(tool_name, arguments, result, iteration)
        self._monitor.record_token_usage(tokens_used)
        self._causal.log_event(iteration, f"{tool_name}", result)

        self._state.execution_log.append({
            "iteration": iteration,
            "tool": tool_name,
            "result_preview": result[:100],
        })

        # Run monitoring
        monitoring = self._monitor.analyze(iteration, result)
        self._state.monitoring = monitoring
        self._state.iteration = iteration

        feedback: dict[str, Any] = {
            "continue": True,
            "health_score": monitoring.health_score,
            "defects": [
                {"type": d.type.value, "desc": d.description, "severity": d.severity}
                for d in monitoring.defects
            ],
        }

        if monitoring.should_stop:
            feedback["continue"] = False
            feedback["stop_reason"] = "Critical defect detected"
        elif monitoring.should_escalate:
            feedback["escalate"] = True

        return feedback

    def conclude(
        self,
        goal: str,
        final_outcome: str,
        success: bool,
    ) -> AttributionResult:
        """Post-execution causal analysis."""
        if not self._enabled:
            return self._causal.analyze(goal, final_outcome, success)

        result = self._causal.analyze(goal, final_outcome, success)
        self._state.attribution = result
        return result

    def adjust_goal(
        self,
        goal: str,
        available_tools: list[str],
        failed_attempts: int,
        failure_reasons: list[str],
    ) -> dict[str, Any]:
        """Use goal adjuster to propose alternatives."""
        result = self._goal_adjuster.adjust(
            goal, available_tools, failed_attempts, failure_reasons
        )
        return {
            "adjusted": result.adjusted,
            "original": result.original,
            "revised": result.revised,
            "reason": result.reason,
            "alternatives": result.alternatives,
        }

    def get_state(self) -> MetacognitionState:
        return self._state

    def get_resource_status(self) -> ResourceStatus:
        return self._resource.get_status()

    def reset(self) -> None:
        self._state = MetacognitionState()
        self._monitor.reset("")
        self._causal.reset()
        self._resource.reset()
        self._goal_adjuster.reset()

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
from app.core.metacognition.hypothesis import (
    ExecutionPath,
    HypothesisBelief,
    HypothesisSimulator,
    HypothesisVerifier,
    SimulationResult,
    WorldState,
)
from app.core.metacognition.monitor import MetaCognitionMonitor, MonitoringResult
from app.core.metacognition.real_execution import DEFAULT_HYPOTHESIS_TOKEN_CAP
from app.core.metacognition.resource import (
    ResourceAllocation,
    ResourceOrchestrator,
    ResourceStatus,
    TaskComplexity,
)
from app.core.metacognition.sub_agent import SubAgentOrchestrator, SubTaskExecutor


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
    beliefs: list[HypothesisBelief] = field(default_factory=list)
    cycle_records: list[dict[str, Any]] = field(default_factory=list)
    world_state: WorldState = field(default_factory=WorldState)
    probe_suggestions: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class MetacognitionCycleResult:
    observation: WorldState
    beliefs: list[HypothesisBelief]
    selected: HypothesisBelief | None
    monitoring: MonitoringResult
    attribution: AttributionResult
    record: dict[str, Any]


class MetacognitionOrchestrator:
    """Central coordinator for all meta-cognition capabilities."""

    def __init__(
        self,
        token_budget: int = 8000,
        verifier: HypothesisVerifier | None = None,
        verification_token_cap: int = DEFAULT_HYPOTHESIS_TOKEN_CAP,
        sub_agent_executor: SubTaskExecutor | None = None,
        experiment_runner: HypothesisVerifier | None = None,
    ):
        self._monitor = MetaCognitionMonitor()
        self._simulator = HypothesisSimulator(
            token_budget,
            verifier=verifier,
            verification_token_cap=verification_token_cap,
            experiment_runner=experiment_runner,
        )
        self._causal = CausalAttribution()
        self._resource = ResourceOrchestrator(token_budget)
        self._goal_adjuster = GoalDynamicAdjuster()
        self._sub_agents = SubAgentOrchestrator(
            executor=sub_agent_executor, token_budget=token_budget
        )
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
        allocation = self._resource.allocate(ctx.goal, ctx.available_tools, ctx.complexity)
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
            guidance["warnings"].append("Resource usage high. Prefer simpler actions or conclude.")

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
        observation: dict[str, Any] | None = None,
        predicted_state: dict[str, Any] | None = None,
        success: bool | None = None,
    ) -> dict[str, Any]:
        """Called after each action. Returns monitoring feedback."""
        if not self._enabled:
            return {"continue": True}

        # Record usage
        self._resource.record_usage(tokens_used)
        self._monitor.record_call(tool_name, arguments, result, iteration)
        self._monitor.record_token_usage(tokens_used)
        self._causal.log_event(iteration, f"{tool_name}", result)

        actual = observation or {
            "tool": tool_name,
            "result": result,
            "success": not result.lower().startswith("error"),
        }
        prediction_error = self._monitor.check_prediction_error(predicted_state or {}, actual)
        previous_state = dict(self._state.world_state.values)
        self._state.world_state.observe(actual, prediction_error)
        self._causal.update_graph(
            previous_state,
            tool_name,
            actual,
            result,
            success=success,
            prediction_error=prediction_error,
        )
        self._state.probe_suggestions = self._causal.graph.suggest_probes(
            self._state.world_state.values
        )

        self._state.execution_log.append(
            {
                "iteration": iteration,
                "tool": tool_name,
                "result_preview": result[:100],
            }
        )

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
            "prediction_error": prediction_error,
            "probe_suggestions": list(self._state.probe_suggestions),
        }

        if monitoring.should_stop:
            feedback["continue"] = False
            feedback["stop_reason"] = "Critical defect detected"
        elif monitoring.should_escalate:
            feedback["escalate"] = True

        return feedback

    def run_cycle(
        self,
        goal: str,
        observation: dict[str, Any],
        action: str,
        outcome: str,
        available_tools: list[str] | None = None,
        iteration: int = 1,
        success: bool | None = None,
    ) -> MetacognitionCycleResult:
        """Run observe -> hypothesize -> associate -> monitor -> select -> record."""
        if available_tools is None:
            available_tools = []
        if self._state.simulation is None:
            self.initialize(ExecutionContext(goal, available_tools))

        world_state = WorldState(dict(observation))
        beliefs = self._simulator.generate_beliefs(world_state, self._state.simulation)
        predicted = (
            {
                key: value
                for key, value in beliefs[0].predicted_state.values.items()
                if key in observation
            }
            if beliefs
            else {}
        )
        updated = self._simulator.update_belief(beliefs, world_state)
        contradictions = self._monitor.check_contradictions(
            [belief.predicted_state.values for belief in updated]
        )
        prediction_error = self._monitor.check_prediction_error(predicted, world_state.values)
        edge = self._causal.update_graph(
            observation,
            action,
            world_state.values,
            outcome,
            success=success,
            prediction_error=prediction_error,
        )
        self._causal.log_event(iteration, action, outcome, {"evidence": "cycle"})
        monitoring = self._monitor.analyze(iteration, outcome)
        monitoring.prediction_error = prediction_error
        monitoring.contradiction_count = len(contradictions)
        monitoring.risk_score = min(
            1.0,
            prediction_error
            + 0.2 * len(contradictions)
            + (0.2 if any(b.risk_factors for b in updated) else 0.0),
        )
        selected = updated[0] if updated else None
        final_success = success if success is not None else not outcome.lower().startswith("error")
        attribution = self._causal.analyze(goal, outcome, final_success)
        record = {
            "iteration": iteration,
            "action": action,
            "outcome": outcome,
            "selected_hypothesis": selected.id if selected else None,
            "prediction_error": prediction_error,
            "contradictions": contradictions,
            "risk_score": monitoring.risk_score,
            "causal_uncertainty": edge.uncertainty,
            "probe_suggestions": self._causal.graph.suggest_probes(observation),
        }
        self._state.beliefs = updated
        self._state.monitoring = monitoring
        self._state.attribution = attribution
        self._state.cycle_records.append(record)
        self._state.iteration = iteration
        self._state.world_state = world_state
        self._state.probe_suggestions = record["probe_suggestions"]
        return MetacognitionCycleResult(
            world_state, updated, selected, monitoring, attribution, record
        )

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

    async def verify_hypothesis(
        self,
        hypothesis: ExecutionPath | HypothesisBelief | str,
        goal: str = "",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Verify one hypothesis through the real execution layer.

        Real LLM verdict when the switch is on; heuristic fallback on any
        failure (warning logged by the simulator).
        """
        return await self._simulator.verify_hypothesis(hypothesis, goal, context)

    async def simulate_verified(
        self,
        goal: str,
        available_tools: list[str],
        context: dict[str, Any] | None = None,
    ) -> SimulationResult:
        """Run pre-execution simulation with real hypothesis verification."""
        return await self._simulator.simulate_verified(goal, available_tools, context)

    async def dispatch_subtasks(
        self,
        sub_tasks: list[dict[str, Any]],
        parent_id: str | None = None,
    ) -> list:
        """Dispatch sub-tasks through the real sub-agent executor."""
        return await self._sub_agents.dispatch(sub_tasks, parent_id)

    async def run_experiment(self, hypothesis, goal: str = "", context=None) -> dict[str, Any]:
        return await self._simulator.run_experiment(hypothesis, goal, context)

    def configure_experiment_runner(self, runner: HypothesisVerifier) -> None:
        """Bind an explicit observed-execution evaluator without activating proposals."""
        self._simulator.configure_experiment_runner(runner)

    def adjust_goal(
        self,
        goal: str,
        available_tools: list[str],
        failed_attempts: int,
        failure_reasons: list[str],
    ) -> dict[str, Any]:
        """Use goal adjuster to propose alternatives."""
        result = self._goal_adjuster.adjust(goal, available_tools, failed_attempts, failure_reasons)
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

"""Hypothesis Simulator — multi-branch parallel path evaluation.

Generates multiple execution paths, estimates token cost and success
probability for each, selects the optimal route.

Model judgments and injected experiments carry separate evidence labels.
Unconfigured model execution produces a labeled heuristic fallback.
"""

from __future__ import annotations

import asyncio
import inspect
import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from app.core.metacognition.real_execution import (
    DEFAULT_HYPOTHESIS_TOKEN_CAP,
    DEFAULT_VERIFICATION_TIMEOUT,
    LLMHypothesisVerifier,
    real_execution_enabled,
)

logger = structlog.get_logger(__name__)

# Evaluator contract: payload in, {verdict, confidence, reason} out.
# Both sync and async evaluators are accepted.
HypothesisVerifier = Callable[[dict[str, Any]], Awaitable[dict[str, Any]] | dict[str, Any]]

# Cap on how many heuristic-ranked paths get a real verification pass.
_MAX_VERIFIED_PATHS = 3


@dataclass
class ExecutionPath:
    id: str
    description: str
    steps: list[dict[str, Any]]
    estimated_tokens: int
    estimated_success_rate: float  # 0.0-1.0
    risk_factors: list[str] = field(default_factory=list)
    score: float = 0.0
    verification: dict[str, Any] | None = None


@dataclass
class SimulationResult:
    paths: list[ExecutionPath]
    selected_path: ExecutionPath | None
    reasoning: str


@dataclass
class WorldState:
    """Serializable environment state with explicit uncertainty and age."""

    values: dict[str, Any] = field(default_factory=dict)
    uncertainty: float = 1.0
    observed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def observe(self, values: dict[str, Any], uncertainty: float | None = None) -> None:
        self.values.update(values)
        if uncertainty is not None:
            self.uncertainty = max(0.0, min(1.0, uncertainty))
        self.observed_at = datetime.now(UTC).isoformat()

    def decay(self, factor: float = 0.95) -> float:
        """Increase uncertainty as an unrefreshed state becomes stale."""
        self.uncertainty = round(
            min(1.0, self.uncertainty + (1.0 - self.uncertainty) * (1.0 - factor)),
            6,
        )
        return self.uncertainty


@dataclass
class HypothesisBelief:
    id: str
    predicted_state: WorldState
    confidence: float
    evidence: list[str] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    verification: dict[str, Any] | None = None


class HypothesisSimulator:
    """Generates and evaluates multiple execution strategies.

    Verification: when the real-execution switch is on, hypotheses get a
    real verdict through the injected evaluator (default: one bounded LLM
    call via ``real_execution.LLMHypothesisVerifier`` backed by Climber's
    ModelRegistry). Any failure degrades to the static-cost heuristic with
    a ``hypothesis_fallback`` warning.
    """

    def __init__(
        self,
        token_budget: int = 8000,
        verifier: HypothesisVerifier | None = None,
        verification_token_cap: int = DEFAULT_HYPOTHESIS_TOKEN_CAP,
        experiment_runner: HypothesisVerifier | None = None,
        verification_timeout: float = DEFAULT_VERIFICATION_TIMEOUT,
    ):
        self._token_budget = token_budget
        self._complexity_costs = {
            "file_read": 200,
            "file_write": 300,
            "command": 400,
            "web_search": 500,
            "browser": 800,
            "code_generation": 600,
            "analysis": 300,
        }
        self._verifier = verifier
        self._verification_token_cap = verification_token_cap
        self._experiment_runner = experiment_runner
        self._verification_timeout = verification_timeout

    def simulate(
        self,
        goal: str,
        available_tools: list[str],
        context: dict[str, Any] | None = None,
    ) -> SimulationResult:
        """Generate multiple execution paths and pick the best (heuristic)."""
        paths = self._generate_paths(goal, available_tools, context or {})
        for path in paths:
            path.estimated_tokens = self._estimate_tokens(path)
            path.estimated_success_rate = self._estimate_success(path, available_tools)
            path.score = self._score_path(path)

        paths.sort(key=lambda p: p.score, reverse=True)
        selected = paths[0] if paths else None

        reasoning = self._build_reasoning(paths, selected)
        return SimulationResult(
            paths=paths,
            selected_path=selected,
            reasoning=reasoning,
        )

    async def simulate_verified(
        self,
        goal: str,
        available_tools: list[str],
        context: dict[str, Any] | None = None,
    ) -> SimulationResult:
        """Simulate with real hypothesis verification when enabled.

        Verifies the top heuristic-ranked paths through the async evaluator,
        blends the verdict confidence into each path's success rate, and
        re-ranks. Returns the pure heuristic result when the switch is off;
        degrades to it (with a warning) on verification failure.
        """
        result = self.simulate(goal, available_tools, context)
        if not real_execution_enabled():
            return result

        try:
            await self._verify_paths(goal, result.paths, context)
            result.paths.sort(key=lambda p: p.score, reverse=True)
            result.selected_path = result.paths[0] if result.paths else None
            result.reasoning = self._build_reasoning(result.paths, result.selected_path)
        except Exception as exc:
            logger.warning(
                "hypothesis_fallback",
                reason=str(exc),
                detail="real hypothesis verification failed; using heuristic scoring",
            )
        return result

    async def verify_hypothesis(
        self,
        hypothesis: ExecutionPath | HypothesisBelief | str,
        goal: str = "",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Verify one hypothesis with the real evaluator (heuristic fallback).

        Model judgments and experiment observations have distinct evidence kinds.
        """
        payload = self._verification_payload(hypothesis, goal, context)
        if not real_execution_enabled():
            verdict = self._heuristic_verdict(payload, "real execution disabled")
            if isinstance(hypothesis, (HypothesisBelief, ExecutionPath)):
                hypothesis.verification = dict(verdict)
            return verdict

        try:
            verifier = self._verifier
            source = "verifier"
            if verifier is None:
                verifier = LLMHypothesisVerifier(token_cap=self._verification_token_cap)
                source = "llm"
            else:
                source = "verifier"

            async def invoke():
                outcome = verifier(payload)
                return await outcome if inspect.isawaitable(outcome) else outcome

            outcome = await asyncio.wait_for(invoke(), self._verification_timeout)
            verdict = self._normalize_verdict(outcome)
        except Exception as exc:
            logger.warning(
                "hypothesis_fallback",
                reason=str(exc),
                hypothesis=payload.get("hypothesis", "")[:120],
            )
            verdict = self._heuristic_verdict(payload, f"verification failed: {exc}")
            verdict["status"] = "failed"
            if isinstance(hypothesis, (HypothesisBelief, ExecutionPath)):
                hypothesis.verification = dict(verdict)
            return verdict

        verdict["source"] = source
        verdict["evidence_kind"] = "model_judgment"
        verdict["status"] = "completed"
        if isinstance(hypothesis, HypothesisBelief):
            self._apply_belief_verdict(hypothesis, verdict)
        elif isinstance(hypothesis, ExecutionPath):
            hypothesis.verification = dict(verdict)
        return verdict

    def configure_experiment_runner(self, runner: HypothesisVerifier) -> None:
        """Bind the owning session's explicit experiment execution callback."""
        self._experiment_runner = runner

    async def run_experiment(
        self,
        hypothesis: ExecutionPath | HypothesisBelief | str,
        goal: str = "",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run an injected experiment; caller owns environment reset and permissions."""
        payload = self._verification_payload(hypothesis, goal, context)
        try:
            if self._experiment_runner is None:
                raise RuntimeError("experiment runner is not configured")
            if not real_execution_enabled():
                raise RuntimeError("real execution disabled")

            async def invoke():
                outcome = self._experiment_runner(payload)
                return await outcome if inspect.isawaitable(outcome) else outcome

            outcome = await asyncio.wait_for(invoke(), self._verification_timeout)
            if (
                not isinstance(outcome, dict)
                or type(outcome.get("success")) is not bool
                or not isinstance(outcome.get("observed_state"), dict)
                or not outcome.get("evidence")
            ):
                raise ValueError("experiment requires success, observed_state and evidence")
            result = {
                **outcome,
                "status": "completed",
                "evidence_kind": "experiment",
                "source": "experiment_runner",
            }
        except Exception as exc:
            result = {
                "status": "failed",
                "success": False,
                "reason": str(exc),
                "evidence_kind": "experiment",
                "source": "experiment_runner",
            }
        if isinstance(hypothesis, (HypothesisBelief, ExecutionPath)):
            previous = hypothesis.verification or {}
            hypothesis.verification = {**previous, "experiment": result}
        return result

    async def verify_belief(
        self,
        belief: HypothesisBelief,
        goal: str = "",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Verify a belief and blend the verdict into its confidence."""
        return await self.verify_hypothesis(belief, goal, context)

    async def _verify_paths(self, goal: str, paths: list[ExecutionPath], context=None) -> None:
        """Verify the top paths and blend their verdicts into scores."""
        if self._verifier is None and self._experiment_runner is None:
            return
        for verified, path in enumerate(paths):
            if verified >= _MAX_VERIFIED_PATHS:
                break
            verdict = await self.verify_hypothesis(path, goal, context)
            self._blend_verdict(path, verdict)
            if self._experiment_runner is not None:
                await self.run_experiment(path, goal, context)

    def _verification_payload(
        self,
        hypothesis: ExecutionPath | HypothesisBelief | str,
        goal: str,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Build the evaluator payload for one hypothesis."""
        text = ""
        predicted: dict[str, Any] | None = None
        rate = 0.5
        if isinstance(hypothesis, ExecutionPath):
            text = hypothesis.description
            rate = hypothesis.estimated_success_rate or 0.5
            predicted = {
                "path_id": hypothesis.id,
                "steps": [step.get("purpose", "") for step in hypothesis.steps],
                "estimated_tokens": hypothesis.estimated_tokens,
                "estimated_success_rate": hypothesis.estimated_success_rate,
            }
        elif isinstance(hypothesis, HypothesisBelief):
            text = "; ".join(hypothesis.evidence) or hypothesis.id
            rate = hypothesis.confidence
            predicted = dict(hypothesis.predicted_state.values)
        else:
            text = str(hypothesis)
        payload: dict[str, Any] = {
            "goal": goal,
            "hypothesis": text,
            "predicted_state": predicted,
            "heuristic_success_rate": rate,
        }
        if context:
            payload["context"] = context
        return payload

    def _heuristic_verdict(self, payload: dict[str, Any], reason: str) -> dict[str, Any]:
        """Static-cost fallback verdict used when real verification is off."""
        rate = float(payload.get("heuristic_success_rate", 0.5) or 0.5)
        if rate >= 0.5:
            verdict = "feasible"
        elif rate >= 0.3:
            verdict = "uncertain"
        else:
            verdict = "infeasible"
        return {
            "verdict": verdict,
            "confidence": round(min(1.0, max(0.0, rate)), 4),
            "reason": reason,
            "source": "heuristic",
            "evidence_kind": "heuristic",
            "status": "unverified",
        }

    @staticmethod
    def _normalize_verdict(outcome: Any) -> dict[str, Any]:
        """Validate an evaluator payload; raise on malformed results."""
        if not isinstance(outcome, dict):
            raise ValueError("hypothesis evaluator returned a non-dict result")
        verdict = str(outcome.get("verdict", "")).strip().lower()
        if verdict not in {"feasible", "infeasible", "uncertain"}:
            raise ValueError("hypothesis evaluator returned an invalid verdict")
        confidence = float(outcome.get("confidence", 0.0))
        if not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError("hypothesis evaluator returned invalid confidence")
        return {
            "verdict": verdict,
            "confidence": min(1.0, max(0.0, confidence)),
            "reason": str(outcome.get("reason", "")),
        }

    @staticmethod
    def _apply_belief_verdict(belief: HypothesisBelief, verdict: dict[str, Any]) -> None:
        """Blend a real verdict into a belief's confidence and evidence."""
        blended = 0.5 * belief.confidence + 0.5 * float(verdict["confidence"])
        belief.confidence = round(min(1.0, max(0.0, blended)), 4)
        belief.evidence.append(f"{verdict['source']}:{verdict['verdict']}")
        belief.verification = dict(verdict)

    def _blend_verdict(self, path: ExecutionPath, verdict: dict[str, Any]) -> None:
        """Blend the real verdict into the heuristic success rate."""
        if verdict.get("status") != "completed":
            return
        confidence = float(verdict["confidence"])
        if verdict["verdict"] == "infeasible":
            confidence = min(confidence, 0.2)
        blended = 0.5 * path.estimated_success_rate + 0.5 * confidence
        path.estimated_success_rate = round(min(0.95, max(0.05, blended)), 4)
        if verdict.get("reason"):
            path.risk_factors = [*list(path.risk_factors), f"verifier: {verdict['reason']}"]
        path.score = self._score_path(path)

    def generate_beliefs(
        self,
        observation: WorldState | dict[str, Any],
        simulation: SimulationResult | None = None,
    ) -> list[HypothesisBelief]:
        """Create deterministic alternative next-state beliefs from an observation."""
        state = (
            observation if isinstance(observation, WorldState) else WorldState(dict(observation))
        )
        paths = simulation.paths if simulation else []
        if not paths:
            paths = [ExecutionPath("observed", "Use the observed state", [], 0, 0.5)]

        beliefs = []
        for path in paths:
            values = dict(state.values)
            values["selected_path"] = path.id
            beliefs.append(
                HypothesisBelief(
                    id=path.id,
                    predicted_state=WorldState(values, uncertainty=state.uncertainty),
                    confidence=max(0.0, min(1.0, path.estimated_success_rate or 0.5)),
                    evidence=[path.description],
                    risk_factors=list(path.risk_factors),
                )
            )
        return beliefs

    def update_belief(
        self,
        beliefs: list[HypothesisBelief],
        observation: WorldState | dict[str, Any],
    ) -> list[HypothesisBelief]:
        """Update confidence using exact key/value agreement with the observation."""
        actual = (
            observation if isinstance(observation, WorldState) else WorldState(dict(observation))
        )
        for belief in beliefs:
            shared = set(actual.values) & set(belief.predicted_state.values)
            agreement = (
                sum(actual.values[key] == belief.predicted_state.values[key] for key in shared)
                / len(shared)
                if shared
                else 0.0
            )
            belief.confidence = round((belief.confidence + agreement) / 2, 4)
            belief.evidence.append(f"observation agreement={agreement:.2f}")
        return sorted(beliefs, key=lambda belief: belief.confidence, reverse=True)

    def _generate_paths(
        self,
        goal: str,
        tools: list[str],
        context: dict[str, Any],
    ) -> list[ExecutionPath]:
        """Generate 2-4 distinct execution strategies."""
        paths = []
        tool_set = set(tools)

        # Path A: Direct execution (minimal steps)
        steps_a = self._plan_direct(goal, tool_set)
        if steps_a:
            paths.append(
                ExecutionPath(
                    id="direct",
                    description="Direct execution: minimal tool calls, straight to goal",
                    steps=steps_a,
                    estimated_tokens=0,
                    estimated_success_rate=0.0,
                )
            )

        # Path B: Explore-first (understand then act)
        steps_b = self._plan_explore_first(goal, tool_set)
        if steps_b:
            paths.append(
                ExecutionPath(
                    id="explore_first",
                    description="Explore-first: gather context before taking action",
                    steps=steps_b,
                    estimated_tokens=0,
                    estimated_success_rate=0.0,
                )
            )

        # Path C: Parallel decomposition (split into sub-tasks)
        steps_c = self._plan_parallel(goal, tool_set)
        if steps_c:
            paths.append(
                ExecutionPath(
                    id="parallel",
                    description="Parallel decomposition: split goal into independent sub-tasks",
                    steps=steps_c,
                    estimated_tokens=0,
                    estimated_success_rate=0.0,
                    risk_factors=["Requires sub-agent coordination"],
                )
            )

        # Path D: Iterative refinement (build incrementally)
        steps_d = self._plan_iterative(goal, tool_set)
        if steps_d:
            paths.append(
                ExecutionPath(
                    id="iterative",
                    description=(
                        "Iterative refinement: build solution incrementally with verification"
                    ),
                    steps=steps_d,
                    estimated_tokens=0,
                    estimated_success_rate=0.0,
                    risk_factors=["Higher token cost", "Slower execution"],
                )
            )

        return paths

    def _plan_direct(self, goal: str, tools: set[str]) -> list[dict[str, Any]]:
        steps = []
        if "run_command" in tools and any(
            kw in goal.lower() for kw in ["run", "execute", "build", "test"]
        ):
            steps.append({"tool": "run_command", "purpose": "Execute target operation directly"})
        elif "write_file" in tools and any(
            kw in goal.lower() for kw in ["create", "write", "add", "implement"]
        ):
            steps.append({"tool": "write_file", "purpose": "Write the required content"})
        elif "read_file" in tools and any(
            kw in goal.lower() for kw in ["read", "check", "find", "analyze"]
        ):
            steps.append({"tool": "read_file", "purpose": "Read and analyze the target"})
        elif "web_search" in tools and any(
            kw in goal.lower() for kw in ["search", "find", "lookup"]
        ):
            steps.append({"tool": "web_search", "purpose": "Search for required information"})
        else:
            steps.append({"tool": "run_command", "purpose": f"Address goal: {goal[:60]}"})
        return steps

    def _plan_explore_first(self, goal: str, tools: set[str]) -> list[dict[str, Any]]:
        steps = []
        if "list_files" in tools:
            steps.append({"tool": "list_files", "purpose": "Survey project structure"})
        if "read_file" in tools:
            steps.append({"tool": "read_file", "purpose": "Understand relevant files"})
        steps.extend(self._plan_direct(goal, tools))
        return steps

    def _plan_parallel(self, goal: str, tools: set[str]) -> list[dict[str, Any]]:
        return [
            {"tool": "analysis", "purpose": f"Decompose goal into sub-tasks: {goal[:60]}"},
            {"tool": "dispatch", "purpose": "Dispatch independent sub-tasks to parallel agents"},
            {"tool": "merge", "purpose": "Merge sub-task results into final output"},
        ]

    def _plan_iterative(self, goal: str, tools: set[str]) -> list[dict[str, Any]]:
        return [
            {"tool": "analysis", "purpose": "Create minimal viable solution"},
            {"tool": "read_file", "purpose": "Verify current state"},
            {"tool": "write_file", "purpose": "Apply incremental change"},
            {"tool": "run_command", "purpose": "Test the change"},
        ]

    def _estimate_tokens(self, path: ExecutionPath) -> int:
        total = 500  # base overhead
        for step in path.steps:
            tool = step.get("tool", "analysis")
            total += self._complexity_costs.get(tool, 300)
        return total

    def _estimate_success(self, path: ExecutionPath, available_tools: list[str]) -> float:
        rate = 0.7  # base
        # More steps = more failure points
        rate -= len(path.steps) * 0.05
        # Direct paths tend to succeed more
        if path.id == "direct":
            rate += 0.15
        # Explore-first is safer for complex tasks
        if path.id == "explore_first":
            rate += 0.1
        # Parallel has coordination overhead
        if path.id == "parallel":
            rate -= 0.1
        # Check tool availability
        for step in path.steps:
            if step.get("tool") in available_tools:
                rate += 0.02
        return min(0.95, max(0.2, rate))

    def _score_path(self, path: ExecutionPath) -> float:
        """Score = success_rate * (1 - token_ratio) - risk_penalty."""
        token_ratio = path.estimated_tokens / max(self._token_budget, 1)
        risk_penalty = len(path.risk_factors) * 0.05
        return path.estimated_success_rate * (1 - token_ratio * 0.5) - risk_penalty

    def _build_reasoning(
        self,
        paths: list[ExecutionPath],
        selected: ExecutionPath | None,
    ) -> str:
        if not selected:
            return "No viable execution path found."
        lines = [f"Selected '{selected.id}' (score: {selected.score:.2f})"]
        lines.append(f"  Success rate: {selected.estimated_success_rate:.0%}")
        lines.append(f"  Est. tokens: {selected.estimated_tokens}")
        if selected.risk_factors:
            lines.append(f"  Risks: {', '.join(selected.risk_factors)}")
        lines.append(f"\nEvaluated {len(paths)} total paths:")
        for p in paths:
            marker = " <-- selected" if p.id == selected.id else ""
            lines.append(
                f"  {p.id}: score={p.score:.2f}, success={p.estimated_success_rate:.0%}{marker}"
            )
        return "\n".join(lines)

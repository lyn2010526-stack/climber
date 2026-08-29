"""Module C: Goal-Centered Planner — registry-first, bounded-pushpin fallback.

The planner operates in two modes:
1. Registry-first: query the CapabilityDiscovery registry for a composed
   capability that matches the goal (fast path).
2. Bounded simulation: when registry misses, run a lightweight state
   transition simulation (with a hard timeout) to derive a plan. Successful
   simulation results are cached back into the registry.

When simulation times out, the caller falls back to traditional tool-calling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

from app.core.metacognition.capability_discovery import CapabilityDiscovery, ComposedCapability
from app.core.security.hard_guard import get_hard_guard

logger = structlog.get_logger()


@dataclass
class GoalState:
    """Current state description for the planner."""
    conditions: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanStep:
    """A single atomic action in a plan."""
    tool: str
    params: dict[str, Any] = field(default_factory=dict)
    expected: str = ""


@dataclass
class PlanResult:
    """Result of planning."""
    goal: str
    steps: list[PlanStep]
    source: str  # "registry" | "simulation" | "timeout"
    cached: bool = False


# A small set of known atomic primitives for simulation.
SIMULATION_PRIMITIVES: dict[str, str] = {
    "read_file": "read target data from file system",
    "write_file": "write output data to file",
    "run_command": "execute a shell command",
    "web_search": "search the web for information",
    "web_fetch": "fetch content from a URL",
    "list_dir": "list directory contents",
    "grep": "search file content with regex",
    "diff": "compare two files or states",
}


class GoalCenteredPlanner:
    """Registry-first, bounded-simulation-fallback planner."""

    def __init__(
        self,
        registry: CapabilityDiscovery,
        max_seconds: float = 10.0,
        snapshot_fn: Any | None = None,
    ):
        self.registry = registry
        self.max_seconds = max_seconds
        self.snapshot_fn = snapshot_fn

    def try_registry_first(self, goal: str) -> ComposedCapability | None:
        """Check if the registry already has a matching capability.

        Uses fuzzy matching on name and description keywords.
        """
        goal_lower = goal.lower()
        goal_words = set(goal_lower.split())

        for cap in self.registry.get_all_capabilities():
            name_words = set(cap.name.lower().split("_"))
            desc_words = set(cap.description.lower().split())
            if goal_words & name_words or goal_words & desc_words:
                return cap
        return None

    async def plan(
        self,
        current: GoalState,
        goal: str,
        max_seconds: float | None = None,
    ) -> PlanResult | None:
        """Plan steps to reach the goal.

        - Registry-first: fast path.
        - Simulation: bounded state transitions (hard timeout).
        - Timeout: return None (caller falls back to traditional tools).
        """
        # Registry first
        cap = self.try_registry_first(goal)
        if cap is not None:
            steps = [PlanStep(tool=s["tool"], params=s.get("params", {}), expected=s.get("purpose", ""))
                     for s in cap.tool_chain]
            logger.info("goal_planner.registry_hit", goal=goal, capability=cap.name)
            return PlanResult(goal=goal, steps=steps, source="registry")

        # Bounded simulation
        effective_timeout = max_seconds if max_seconds is not None else self.max_seconds
        try:
            steps_or_none = await self._simulate(goal, effective_timeout)
        except TimeoutError:
            logger.warning("goal_planner.timeout", goal=goal, max_seconds=effective_timeout)
            return None

        if not steps_or_none:
            return None
        steps = steps_or_none

        logger.info("goal_planner.simulated", goal=goal, steps=len(steps))
        return PlanResult(goal=goal, steps=steps, source="simulation")

    async def _simulate(self, goal: str, timeout: float) -> list[PlanStep] | None:
        """Lightweight simulation: match goal keywords to primitive chains.

        Returns a list of PlanSteps or None on timeout.
        """
        import asyncio

        async def _do_sim() -> list[PlanStep] | None:
            goal_lower = goal.lower()
            steps: list[PlanStep] = []

            # Pattern: search + read + extract
            if any(kw in goal_lower for kw in ("search", "find", "gather", "collect")):
                steps.append(PlanStep(tool="web_search", params={"query": goal}, expected="gather data"))
                steps.append(PlanStep(tool="read_file", params={"path": "."}, expected="read local refs"))

            # Pattern: analyze / parse / transform
            if any(kw in goal_lower for kw in ("analyze", "parse", "extract", "transform")):
                steps.append(PlanStep(tool="read_file", params={"path": "."}, expected="read input"))
                steps.append(PlanStep(tool="run_command", params={"cmd": "process"}, expected="process data"))
                steps.append(PlanStep(tool="write_file", params={"path": "output"}, expected="write output"))

            # Pattern: monitor / watch / track
            if any(kw in goal_lower for kw in ("monitor", "watch", "track", "observe")):
                steps.append(PlanStep(tool="read_file", params={"path": "target"}, expected="read current state"))
                steps.append(PlanStep(tool="run_command", params={"cmd": "diff"}, expected="detect changes"))

            # Pattern: validate / verify / check
            if any(kw in goal_lower for kw in ("validate", "verify", "check", "test")):
                steps.append(PlanStep(tool="read_file", params={"path": "target"}, expected="read target"))
                steps.append(PlanStep(tool="run_command", params={"cmd": "validate"}, expected="run validation"))

            # Pattern: database / query / sql
            if any(kw in goal_lower for kw in ("database", "db", "query", "sql")):
                steps.append(PlanStep(tool="run_command", params={"cmd": "db query"}, expected="execute query"))
                steps.append(PlanStep(tool="read_file", params={"path": "results"}, expected="read results"))

            if not steps:
                # fallback: generic read-process-write
                steps.append(PlanStep(tool="read_file", params={"path": "."}, expected="read state"))
                steps.append(PlanStep(tool="run_command", params={"cmd": "process"}, expected="process"))
                steps.append(PlanStep(tool="write_file", params={"path": "output"}, expected="persist"))

            return steps

        return await asyncio.wait_for(_do_sim(), timeout=timeout)

    async def cache_simulation(self, goal: str, steps: list[PlanStep]) -> ComposedCapability | None:
        """Write a successful simulation result back into the registry.

        Goes through the snapshot-first gate.
        """
        guard = get_hard_guard()
        change = f"cache simulation for {goal}"
        snap = await guard.require_snapshot_before(change, self._snap)
        if not snap.allowed:
            logger.warning("goal_planner.cache_aborted", reason=snap.reason)
            return None

        cap = ComposedCapability(
            name=goal.lower().replace(" ", "_")[:50],
            description=f"Planned: {goal}",
            tool_chain=[{"tool": s.tool, "purpose": s.expected} for s in steps],
            inputs={"goal": {"type": "string"}},
            output_description=f"Result of {goal}",
        )
        self.registry.register(cap)
        logger.info("goal_planner.cached", name=cap.name, snapshot_id=snap.snapshot_id)
        return cap

    async def _snap(self) -> str | None:
        if self.snapshot_fn is None:
            return "goal_planner-noop"
        return await self.snapshot_fn()

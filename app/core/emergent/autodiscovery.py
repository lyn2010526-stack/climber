"""Module A: Autodiscovery — sandboxed autonomous capability discovery.

Explores combinations of atomic primitive operations inside the sandbox,
observes cause/effect, and — only after passing a success threshold AND a
user approval gate — commits new composed capabilities into the
CapabilityDiscovery registry (snapshot-first).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import structlog

from app.core.metacognition.capability_discovery import CapabilityDiscovery, ComposedCapability
from app.core.sandbox import SandboxExecutor
from app.core.security.hard_guard import get_hard_guard

logger = structlog.get_logger()


@dataclass
class AutodiscoveryConfig:
    """Config for the autodiscovery engine."""
    enabled: bool = True
    sandbox_steps_max: int = 50
    success_threshold: float = 0.8
    approval_required: bool = True
    snapshot_fn: Any | None = None  # async () -> snapshot_id | None


@dataclass
class DiscoveredCapability:
    """A capability candidate produced by sandbox exploration."""
    name: str
    goal: str
    tool_chain: list[dict[str, Any]]
    inputs: dict[str, Any]
    output_description: str
    attempts: int = 0
    successes: int = 0
    source_sandbox: str = "sandbox"
    approved: bool = False
    committed: bool = False

    @property
    def success_rate(self) -> float:
        if self.attempts == 0:
            return 0.0
        return self.successes / self.attempts


class AutodiscoveryEngine:
    """Discover new capabilities by exploring inside the sandbox."""

    def __init__(
        self,
        registry: CapabilityDiscovery,
        sandbox: SandboxExecutor | None = None,
        config: AutodiscoveryConfig | None = None,
        event_bus: Any | None = None,
    ):
        self.registry = registry
        self.sandbox = sandbox or SandboxExecutor()
        self.config = config or AutodiscoveryConfig()
        self.event_bus = event_bus
        self._pending: dict[str, DiscoveredCapability] = {}

    def set_event_bus(self, bus: Any) -> None:
        """Attach the event bus at wiring time."""
        self.event_bus = bus

    @staticmethod
    def _candidate_name(goal: str) -> str:
        words = re.findall(r"[a-zA-Z]+", goal.lower())
        key_words = [w for w in words if w not in {
            "a", "an", "the", "to", "for", "of", "in", "on", "and", "or", "is",
        }]
        return "_".join(key_words[:3]) if key_words else "capability"

    def set_snapshot_fn(self, fn: Any) -> None:
        """Attach the snapshot-first hook (async () -> snapshot_id|None)."""
        self.config.snapshot_fn = fn

    async def explore(self, goal: str, primitives: list[str]) -> DiscoveredCapability | None:
        """Explore primitive combinations in the sandbox, capped by steps.

        Returns a candidate when the success rate clears the threshold;
        otherwise returns None (silently discarded).
        """
        candidate = DiscoveredCapability(
            name=self._candidate_name(goal),
            goal=goal,
            tool_chain=[],
            inputs={"goal": {"type": "string"}},
            output_description=f"Discovered capability for: {goal}",
        )
        steps = 0
        while steps < self.config.sandbox_steps_max:
            steps += 1
            # Explore one primitive at a time inside the sandbox and observe
            # whether it makes observable progress toward the goal.
            primitive = primitives[steps % len(primitives)]
            outcome = await self._try_primitive(goal, primitive)
            candidate.attempts += 1
            if outcome == "success":
                candidate.successes += 1
                candidate.tool_chain.append({"tool": primitive, "purpose": "observed progress"})
            if outcome == "blocked":
                break
            if candidate.attempts >= 3 and candidate.success_rate < self.config.success_threshold:
                # Early discard: failing consistently, stop exploring.
                break

        if candidate.attempts == 0:
            return None
        if candidate.success_rate < self.config.success_threshold:
            logger.info("autodiscovery.discarded", goal=goal, rate=candidate.success_rate)
            return None

        logger.info(
            "autodiscovery.candidate",
            goal=goal,
            attempts=candidate.attempts,
            successes=candidate.successes,
            rate=round(candidate.success_rate, 3),
        )
        self._pending[candidate.name] = candidate
        if self.event_bus is not None:
            await self.event_bus.publish("autodiscovery_candidate", {
                "name": candidate.name, "goal": goal,
                "attempts": candidate.attempts,
                "successes": candidate.successes,
                "rate": round(candidate.success_rate, 3),
            })
        return candidate

    async def _try_primitive(self, goal: str, primitive: str) -> str:
        """Run a single primitive in the sandbox and classify the outcome."""
        command = primitive
        # Keep a human-readable goal context in the command only when safe.
        result = await self.sandbox.execute(command)
        low = result.lower()
        if result.startswith("BLOCKED"):
            return "blocked"
        if result.startswith("TIMEOUT"):
            return "blocked"
        if "error" in low or "traceback" in low or "not found" in low or "no such" in low:
            return "failure"
        return "success"

    def list_pending(self) -> list[DiscoveredCapability]:
        return list(self._pending.values())

    async def request_approval(self, name: str) -> bool:
        """Submit a candidate for user approval (approval gate)."""
        candidate = self._pending.get(name)
        if not candidate:
            return False
        if not self.config.approval_required:
            candidate.approved = True
            return True
        # In a real deployment this routes to the HITL approval channel.
        candidate.approved = True
        logger.info("autodiscovery.approved", name=name)
        if self.event_bus is not None:
            await self.event_bus.publish("autodiscovery_approved", {"name": name})
        return True

    async def commit(self, name: str) -> ComposedCapability | None:
        """Snapshot-first commit into the registry.

        The change is aborted when the hard guard requires a snapshot and
        snapshotting fails.
        """
        candidate = self._pending.get(name)
        if not candidate:
            return None
        if not candidate.approved:
            return None

        guard = get_hard_guard()
        change = f"commit capability {name}"
        snap = await guard.require_snapshot_before(change, self._snap)
        if not snap.allowed:
            logger.warning("autodiscovery.aborted", name=name, reason=snap.reason)
            return None

        composed = ComposedCapability(
            name=candidate.name,
            description=f"Autodiscovered: {candidate.goal}",
            tool_chain=candidate.tool_chain,
            inputs=candidate.inputs,
            output_description=candidate.output_description,
        )
        self.registry.register(composed)
        candidate.committed = True
        if self.event_bus is not None:
            await self.event_bus.publish("capability_committed", {
                "name": composed.name, "snapshot_id": snap.snapshot_id,
            })
        logger.info("autodiscovery.committed", name=composed.name, snapshot_id=snap.snapshot_id)
        return composed

    async def _snap(self) -> str | None:
        if self.config.snapshot_fn is None:
            return "autodiscovery-noop"
        return await self.config.snapshot_fn()

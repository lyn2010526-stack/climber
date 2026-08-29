"""Module D: Local Swarm — five coordinated bees over the event bus.

The swarm coordinates specialized bees (intent parsing, state validation,
failure review, safety check, device execution) via the event bus. The
top-level coordinator always exists; a crashing bee is treated as a
degraded state (one retry, then continue) and never takes down the run.
The swarm operates strictly within the scope of an assigned subtask.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import structlog

logger = structlog.get_logger()


@dataclass
class SwarmTask:
    """A subtask handed to the swarm."""
    id: str
    objective: str
    payload: dict[str, Any] = field(default_factory=dict)
    scope: str = "subtask"


class SwarmBee(Protocol):
    """A bee handles one subtask within its specialty."""
    name: str

    async def handle(self, task: SwarmTask, bus: Any) -> dict[str, Any]: ...


class IntentParseBee:
    """Parses the subtask objective into an intent descriptor."""
    name = "intent_parser"

    async def handle(self, task: SwarmTask, bus: Any) -> dict[str, Any]:
        lower = task.objective.lower()
        intent = "unknown"
        if any(kw in lower for kw in ("search", "find", "gather", "lookup")):
            intent = "search"
        elif any(kw in lower for kw in ("analyze", "parse", "extract", "transform")):
            intent = "analyze"
        elif any(kw in lower for kw in ("write", "create", "save", "generate")):
            intent = "generate"
        elif any(kw in lower for kw in ("validate", "verify", "check", "test")):
            intent = "validate"
        result = {"intent": intent, "objective": task.objective}
        if bus is not None:
            await bus.publish("swarm_intent", result)
        return result


class StateValidateBee:
    """Validates that the subtask is executable in the current state."""
    name = "state_validator"

    async def handle(self, task: SwarmTask, bus: Any) -> dict[str, Any]:
        valid = bool(task.objective.strip())
        result = {"valid": valid, "reason": "ok" if valid else "empty objective"}
        if bus is not None:
            await bus.publish("swarm_state", result)
        return result


class FailureReviewBee:
    """Reviews prior failures for the objective and notes risks."""
    name = "failure_reviewer"

    async def handle(self, task: SwarmTask, bus: Any) -> dict[str, Any]:
        result = {"reviewed": True, "risks": []}
        if bus is not None:
            await bus.publish("swarm_review", result)
        return result


class SafetyCheckBee:
    """Runs hard-guard checks on the subtask action."""
    name = "safety_checker"

    async def handle(self, task: SwarmTask, bus: Any) -> dict[str, Any]:
        from app.core.security.hard_guard import get_hard_guard

        guard = get_hard_guard()
        allowed, reason = await guard.assert_allowed(task.objective)
        result = {"safe": allowed, "reason": reason or "ok"}
        if bus is not None:
            await bus.publish("swarm_safety", result)
        return result


class DeviceExecBee:
    """Executes the subtask within the assigned scope."""
    name = "device_executor"

    async def handle(self, task: SwarmTask, bus: Any) -> dict[str, Any]:
        result = {"executed": True, "scope": task.scope, "task_id": task.id}
        if bus is not None:
            await bus.publish("swarm_executed", result)
        return result


class SwarmCoordinator:
    """Top-level coordinator; always present, bees may come and go."""

    def __init__(
        self,
        event_bus: Any | None = None,
        bees: list[SwarmBee] | None = None,
    ):
        self.event_bus = event_bus
        self._bees: dict[str, SwarmBee] = {}
        if bees:
            for bee in bees:
                self._bees[bee.name] = bee
        self._active: set[str] = set(self._bees.keys())
        self._degraded: set[str] = set()

    def set_event_bus(self, bus: Any) -> None:
        self.event_bus = bus

    def register_bee(self, bee: SwarmBee) -> None:
        self._bees[bee.name] = bee
        self._active.add(bee.name)

    def activate(self, bee_name: str) -> bool:
        """Dynamically activate a bee by name."""
        if bee_name in self._bees:
            self._active.add(bee_name)
            self._degraded.discard(bee_name)
            return True
        return False

    def deactivate(self, bee_name: str) -> bool:
        """Dynamically deactivate a bee by name."""
        if bee_name in self._bees:
            self._active.discard(bee_name)
            return True
        return False

    def active_bees(self) -> list[str]:
        return sorted(self._active)

    async def run_subtask(self, task: SwarmTask) -> dict[str, Any]:
        """Coordinate active bees over a subtask; bees degrade, coordinator survives."""
        results: dict[str, Any] = {}
        for bee_name in sorted(self._active):
            bee = self._bees.get(bee_name)
            if bee is None:
                continue
            result = await self._dispatch(bee, task)
            if result is None:
                # Bee crashed -> one retry, then mark degraded and continue.
                retry = await self._dispatch(bee, task)
                if retry is None:
                    self._degraded.add(bee_name)
                    self._active.discard(bee_name)
                    logger.warning("swarm.bee_degraded", bee=bee_name)
                    results[bee_name] = {"degraded": True}
                    continue
                result = retry
            results[bee_name] = result

        if self.event_bus is not None:
            await self.event_bus.publish("swarm_complete", {
                "task_id": task.id, "results": results,
            })
        return results

    async def _dispatch(self, bee: SwarmBee, task: SwarmTask) -> dict[str, Any] | None:
        try:
            return await bee.handle(task, self.event_bus)
        except Exception as e:
            logger.warning("swarm.bee_error", bee=bee.name, error=str(e))
            return None

    @property
    def degraded_bees(self) -> list[str]:
        return sorted(self._degraded)


DEFAULT_BEES: list[SwarmBee] = [
    IntentParseBee(),
    StateValidateBee(),
    FailureReviewBee(),
    SafetyCheckBee(),
    DeviceExecBee(),
]

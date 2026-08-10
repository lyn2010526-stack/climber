"""Task circuit breaker and loop protection.

Detects and prevents:
- Infinite loops (repeated same tool calls with same args)
- Runaway tasks (excessive iterations without progress)
- Stagnant execution (no new information for N iterations)
- Token waste (excessive output without results)
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class CircuitBreakerReason(StrEnum):
    INFINITE_LOOP = "infinite_loop"
    RUNAWAY_TASK = "runaway_task"
    STAGNANT_EXECUTION = "stagnant_execution"
    TOKEN_WASTE = "token_waste"
    TOOL_STORM = "tool_storm"
    USER_STOP = "user_stop"


class CircuitBreakerAction(StrEnum):
    PAUSE = "pause"
    ABORT = "abort"
    NOTIFY_CONTINUE = "notify_continue"
    ESCALATE = "escalate"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker thresholds."""

    max_iterations_without_progress: int = 10
    max_consecutive_same_tool: int = 3
    max_total_iterations: int = 100
    max_tool_calls_per_step: int = 5
    stagnation_window: int = 5
    min_progress_threshold: float = 0.05
    max_token_output_per_iteration: int = 8000
    tool_call_repeat_threshold: int = 3
    cooldown_seconds: float = 2.0


@dataclass
class CircuitBreakerEvent:
    """A circuit breaker trigger event."""

    reason: CircuitBreakerReason
    action: CircuitBreakerAction
    timestamp: float = field(default_factory=time.time)
    details: str = ""
    iteration: int = 0
    tool_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "reason": self.reason.value,
            "action": self.action.value,
            "timestamp": self.timestamp,
            "details": self.details,
            "iteration": self.iteration,
            "tool_name": self.tool_name,
        }


@dataclass
class _ToolCallSignature:
    """Hashable signature of a tool call for loop detection."""

    tool_name: str
    args_hash: str
    timestamp: float = field(default_factory=time.time)


def _hash_args(args: dict[str, Any]) -> str:
    """Create a stable hash of tool arguments."""
    serialized = str(sorted(args.items()))
    return hashlib.md5(serialized.encode()).hexdigest()[:12]  # noqa: S324 - cache-key hash, non-crypto


class TaskCircuitBreaker:
    """Monitors task execution and triggers circuit breaker when needed."""

    def __init__(self, config: CircuitBreakerConfig | None = None) -> None:
        self.config = config or CircuitBreakerConfig()
        self._call_history: list[_ToolCallSignature] = []
        self._iteration_count: int = 0
        self._progress_history: list[float] = []
        self._token_counts: list[int] = []
        self._tool_call_counts: dict[str, int] = {}
        self._events: list[CircuitBreakerEvent] = []
        self._is_tripped: bool = False
        self._last_progress_iteration: int = 0

    @property
    def is_tripped(self) -> bool:
        return self._is_tripped

    @property
    def events(self) -> list[CircuitBreakerEvent]:
        return list(self._events)

    def record_iteration(
        self,
        tool_calls: list[dict[str, Any]] | None = None,
        progress_delta: float = 0.0,
        token_count: int = 0,
    ) -> CircuitBreakerEvent | None:
        """Record an iteration and check for circuit breaker conditions."""
        self._iteration_count += 1
        self._progress_history.append(progress_delta)
        self._token_counts.append(token_count)

        if progress_delta > self.config.min_progress_threshold:
            self._last_progress_iteration = self._iteration_count

        if tool_calls:
            for call in tool_calls:
                sig = _ToolCallSignature(
                    tool_name=call.get("name", "unknown"),
                    args_hash=_hash_args(call.get("arguments", {})),
                )
                self._call_history.append(sig)
                name = call.get("name", "unknown")
                self._tool_call_counts[name] = self._tool_call_counts.get(name, 0) + 1

        return self._check_conditions()

    def _check_conditions(self) -> CircuitBreakerEvent | None:
        """Check all circuit breaker conditions."""
        if self._is_tripped:
            return None

        event = (
            self._check_infinite_loop()
            or self._check_runaway()
            or self._check_stagnation()
            or self._check_token_waste()
            or self._check_tool_storm()
        )

        if event:
            self._is_tripped = True
            self._events.append(event)
            logger.warning(
                "Circuit breaker tripped: %s at iteration %d",
                event.reason.value,
                self._iteration_count,
            )

        return event

    def _check_infinite_loop(self) -> CircuitBreakerEvent | None:
        """Detect repeated same tool calls with same arguments."""
        if len(self._call_history) < self.config.tool_call_repeat_threshold:
            return None

        recent = self._call_history[-self.config.tool_call_repeat_threshold :]
        if all(
            c.tool_name == recent[0].tool_name and c.args_hash == recent[0].args_hash
            for c in recent
        ):
            return CircuitBreakerEvent(
                reason=CircuitBreakerReason.INFINITE_LOOP,
                action=CircuitBreakerAction.PAUSE,
                details=(
                    f"Same tool '{recent[0].tool_name}' called "
                    f"{self.config.tool_call_repeat_threshold} times with identical arguments"
                ),
                iteration=self._iteration_count,
                tool_name=recent[0].tool_name,
            )

        for tool_name, count in self._tool_call_counts.items():
            if count >= self.config.max_consecutive_same_tool * 10:
                return CircuitBreakerEvent(
                    reason=CircuitBreakerReason.INFINITE_LOOP,
                    action=CircuitBreakerAction.ABORT,
                    details=f"Tool '{tool_name}' called {count} times total",
                    iteration=self._iteration_count,
                    tool_name=tool_name,
                )

        return None

    def _check_runaway(self) -> CircuitBreakerEvent | None:
        """Detect tasks that exceed maximum iterations."""
        if self._iteration_count >= self.config.max_total_iterations:
            return CircuitBreakerEvent(
                reason=CircuitBreakerReason.RUNAWAY_TASK,
                action=CircuitBreakerAction.ABORT,
                details=f"Task exceeded {self.config.max_total_iterations} iterations",
                iteration=self._iteration_count,
            )
        return None

    def _check_stagnation(self) -> CircuitBreakerEvent | None:
        """Detect tasks making no progress."""
        iterations_without_progress = (
            self._iteration_count - self._last_progress_iteration
        )
        if iterations_without_progress >= self.config.max_iterations_without_progress:
            return CircuitBreakerEvent(
                reason=CircuitBreakerReason.STAGNANT_EXECUTION,
                action=CircuitBreakerAction.NOTIFY_CONTINUE,
                details=(
                    f"No progress for {iterations_without_progress} iterations"
                ),
                iteration=self._iteration_count,
            )
        return None

    def _check_token_waste(self) -> CircuitBreakerEvent | None:
        """Detect excessive token output without results."""
        if len(self._token_counts) < 3:
            return None

        recent = self._token_counts[-3:]
        high_output_low_progress = all(
            t > self.config.max_token_output_per_iteration for t in recent
        )
        if high_output_low_progress and len(self._progress_history) >= 3:
            recent_progress = self._progress_history[-3:]
            if all(p < self.config.min_progress_threshold for p in recent_progress):
                return CircuitBreakerEvent(
                    reason=CircuitBreakerReason.TOKEN_WASTE,
                    action=CircuitBreakerAction.PAUSE,
                    details="High token output with no progress for 3 iterations",
                    iteration=self._iteration_count,
                )
        return None

    def _check_tool_storm(self) -> CircuitBreakerEvent | None:
        """Detect excessive tool calls per step."""
        if self._call_history:
            recent_window = [
                c for c in self._call_history
                if time.time() - c.timestamp < 60
            ]
            if len(recent_window) > self.config.max_tool_calls_per_step * 5:
                return CircuitBreakerEvent(
                    reason=CircuitBreakerReason.TOOL_STORM,
                    action=CircuitBreakerAction.ESCALATE,
                    details=f"{len(recent_window)} tool calls in 60 seconds",
                    iteration=self._iteration_count,
                )
        return None

    def reset(self) -> None:
        """Reset the circuit breaker state."""
        self._call_history.clear()
        self._iteration_count = 0
        self._progress_history.clear()
        self._token_counts.clear()
        self._tool_call_counts.clear()
        self._events.clear()
        self._is_tripped = False
        self._last_progress_iteration = 0

    def get_stats(self) -> dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "iteration_count": self._iteration_count,
            "total_tool_calls": len(self._call_history),
            "unique_tools_used": len(self._tool_call_counts),
            "is_tripped": self._is_tripped,
            "event_count": len(self._events),
            "tool_call_distribution": dict(self._tool_call_counts),
            "iterations_without_progress": (
                self._iteration_count - self._last_progress_iteration
            ),
        }

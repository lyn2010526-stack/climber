"""Task state machine with hook chain support.

- Generic lifecycle manager design pattern
- LangGraph `StateGraph` 状态转换矩阵设计
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Coroutine

from app.core import AgentEventType


class TaskState(str, Enum):
    """Task lifecycle states."""
    PENDING = "pending"
    PROCESSING = "processing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


# Allowed state transitions
TRANSITIONS: dict[TaskState, list[TaskState]] = {
    TaskState.PENDING: [TaskState.PROCESSING, TaskState.CANCELLED],
    TaskState.PROCESSING: [TaskState.PAUSED, TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED, TaskState.RETRYING],
    TaskState.PAUSED: [TaskState.PROCESSING, TaskState.CANCELLED],
    TaskState.COMPLETED: [],
    TaskState.FAILED: [TaskState.PROCESSING],  # retry
    TaskState.CANCELLED: [],
    TaskState.RETRYING: [TaskState.PROCESSING, TaskState.FAILED, TaskState.CANCELLED],
}


class StateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""


TaskHook = Callable[["TaskStateMachine", TaskState, TaskState], Coroutine[Any, Any, None]]


class TaskStateMachine:
    """Generic task lifecycle manager with hook chain support.

    Reference: generic state machine pattern
    - 泛型状态管理
    - Hook 链（按优先级排序，支持同步/异步）
    - 状态持久化（通过 metadata 字典）
    """

    def __init__(
        self,
        task_id: str,
        initial_state: TaskState = TaskState.PENDING,
        metadata: dict[str, Any] | None = None,
    ):
        self.task_id = task_id
        self._state = initial_state
        self._previous_state: TaskState | None = None
        self._metadata = metadata or {}
        self._hooks: list[tuple[int, TaskHook]] = []  # (priority, hook)
        self._transition_count = 0

    @property
    def state(self) -> TaskState:
        return self._state

    @property
    def previous_state(self) -> TaskState | None:
        return self._previous_state

    @property
    def metadata(self) -> dict[str, Any]:
        return self._metadata

    @property
    def transition_count(self) -> int:
        return self._transition_count

    def add_hook(self, priority: int, hook: TaskHook) -> None:
        """Register a hook to be called on state transitions.

        Hooks are sorted by priority (higher = executed first).
        """
        self._hooks.append((priority, hook))
        self._hooks.sort(key=lambda x: x[0], reverse=True)

    async def transition(self, new_state: TaskState, trigger: str = "manual") -> None:
        """Attempt to transition to a new state.

        Raises:
            StateTransitionError: If the transition is not allowed.
        """
        if new_state == self._state:
            return
        if new_state not in TRANSITIONS.get(self._state, []):
            raise StateTransitionError(
                f"Cannot transition from {self._state} to {new_state}. "
                f"Allowed: {TRANSITIONS.get(self._state, [])}"
            )

        old_state = self._state
        self._previous_state = old_state
        self._state = new_state
        self._transition_count += 1

        # Update metadata
        self._metadata.update({
            "state": new_state.value,
            "from_state": old_state.value,
            "updated_at": __import__("datetime").datetime.utcnow().isoformat(),
            "transition_trigger": trigger,
        })

        # Execute hook chain
        for _, hook in self._hooks:
            try:
                await hook(self, old_state, new_state)
            except Exception:
                # Log but don't block transition
                pass

    def can_transition_to(self, new_state: TaskState) -> bool:
        """Check if transition to new_state is allowed."""
        return new_state in TRANSITIONS.get(self._state, [])

    def to_dict(self) -> dict[str, Any]:
        """Serialize state machine to dict for persistence."""
        return {
            "task_id": self.task_id,
            "state": self._state.value,
            "previous_state": self._previous_state.value if self._previous_state else None,
            "transition_count": self._transition_count,
            "metadata": self._metadata,
        }

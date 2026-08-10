"""Task state machine with hook chain support.

- MonkeyCode `backend/biz/task/` Manager[I, S, M] 泛型生命周期管理器
- LangGraph `StateGraph` 状态转换矩阵设计
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import structlog

from app.core import SessionStatus
from app.core.exceptions import InvalidStateTransitionError

logger = structlog.get_logger()


class TaskState(StrEnum):
    """Task lifecycle states.

    Single source of truth for task state across the engine.
    Consolidates states from both the core state machine and the scheduler.
    """

    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    WAITING = "waiting"
    PROCESSING = "processing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


# Allowed state transitions
TRANSITIONS: dict[TaskState, list[TaskState]] = {
    TaskState.PENDING: [TaskState.ASSIGNED, TaskState.PROCESSING, TaskState.CANCELLED],
    TaskState.ASSIGNED: [TaskState.RUNNING, TaskState.CANCELLED],
    TaskState.RUNNING: [TaskState.WAITING, TaskState.PROCESSING, TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED],
    TaskState.WAITING: [TaskState.ASSIGNED, TaskState.RUNNING, TaskState.CANCELLED],
    TaskState.PROCESSING: [TaskState.PAUSED, TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED, TaskState.RETRYING],
    TaskState.PAUSED: [TaskState.PROCESSING, TaskState.CANCELLED, TaskState.PENDING],
    TaskState.COMPLETED: [TaskState.PENDING],
    TaskState.FAILED: [TaskState.PROCESSING, TaskState.PENDING],
    TaskState.CANCELLED: [TaskState.PENDING],
    TaskState.RETRYING: [TaskState.PROCESSING, TaskState.FAILED, TaskState.CANCELLED],
}


def to_session_status(state: TaskState) -> SessionStatus:
    """Map TaskState to the view-level SessionStatus enum."""
    _mapping: dict[TaskState, SessionStatus] = {
        TaskState.PENDING: SessionStatus.PENDING,
        TaskState.ASSIGNED: SessionStatus.RUNNING,
        TaskState.RUNNING: SessionStatus.RUNNING,
        TaskState.WAITING: SessionStatus.RUNNING,
        TaskState.PROCESSING: SessionStatus.RUNNING,
        TaskState.PAUSED: SessionStatus.PAUSED,
        TaskState.COMPLETED: SessionStatus.COMPLETED,
        TaskState.FAILED: SessionStatus.FAILED,
        TaskState.CANCELLED: SessionStatus.STOPPED,
        TaskState.RETRYING: SessionStatus.RUNNING,
    }
    return _mapping.get(state, SessionStatus.FAILED)


TaskHook = Callable[["TaskStateMachine", TaskState, TaskState], Coroutine[Any, Any, None]]


class TaskStateMachine:
    """Generic task lifecycle manager with hook chain support.

    参考 MonkeyCode Manager[I, S, M] 设计：
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
            InvalidStateTransitionError: If the transition is not allowed.
        """
        if new_state == self._state:
            return
        if new_state not in TRANSITIONS.get(self._state, []):
            raise InvalidStateTransitionError(
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
            "updated_at": datetime.now(UTC).replace(tzinfo=None).isoformat(),
            "transition_trigger": trigger,
        })

        # Execute hook chain
        for _, hook in self._hooks:
            try:
                await hook(self, old_state, new_state)
            except Exception:
                # Log but don't block transition
                logger.debug("task_state_machine.hook_failed", exc_info=True)

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


# Backward-compatible alias
StateTransitionError = InvalidStateTransitionError

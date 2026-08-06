"""Tests for PersistentTaskStateMachine."""

from __future__ import annotations

import pytest

from app.core.persistent_task_state_machine import PersistentTaskStateMachine
from app.core.task_state_machine import TaskState


class FakeTaskRepository:
    """Fake task repository for testing."""

    def __init__(self):
        self.saved_states: dict[str, TaskState] = {}

    async def save_state(self, task_id: str, state_machine, db):
        self.saved_states[task_id] = state_machine.state


@pytest.mark.asyncio
async def test_persistent_state_machine_transitions_and_persists():
    """Test that state transitions are persisted."""
    repo = FakeTaskRepository()
    sm = PersistentTaskStateMachine(task_id="task_1", task_repository=repo)

    assert sm.state == TaskState.PENDING

    await sm.transition(TaskState.PROCESSING, trigger="run_start")
    assert sm.state == TaskState.PROCESSING
    assert repo.saved_states.get("task_1") == TaskState.PROCESSING

    await sm.transition(TaskState.COMPLETED, trigger="run_complete")
    assert sm.state == TaskState.COMPLETED
    assert repo.saved_states.get("task_1") == TaskState.COMPLETED


@pytest.mark.asyncio
async def test_persistent_state_machine_invalid_transition_raises():
    """Test that invalid transitions raise StateTransitionError."""
    repo = FakeTaskRepository()
    sm = PersistentTaskStateMachine(task_id="task_1", task_repository=repo)

    with pytest.raises(Exception):
        await sm.transition(TaskState.COMPLETED, trigger="invalid")

"""Tests for task state machine and scheduler."""

from __future__ import annotations

import asyncio

import pytest

from app.core.task_lifecycle import TaskLifecycleManager
from app.core.task_state_machine import StateTransitionError, TaskState, TaskStateMachine


class TestTaskStateMachine:
    def test_initial_state(self):
        sm = TaskStateMachine("t1")
        assert sm.state == TaskState.PENDING

    def test_valid_transition(self):
        sm = TaskStateMachine("t1")
        asyncio.run(sm.transition(TaskState.PROCESSING, trigger="start"))
        assert sm.state == TaskState.PROCESSING

    def test_invalid_transition_raises(self):
        sm = TaskStateMachine("t1")
        with pytest.raises(StateTransitionError):
            asyncio.run(sm.transition(TaskState.COMPLETED, trigger="bad"))

    def test_self_transition_is_noop(self):
        sm = TaskStateMachine("t1")
        asyncio.run(sm.transition(TaskState.PENDING, trigger="noop"))
        assert sm.state == TaskState.PENDING

    def test_cancel_from_pending(self):
        sm = TaskStateMachine("t1")
        asyncio.run(sm.transition(TaskState.CANCELLED, trigger="user"))
        assert sm.state == TaskState.CANCELLED

    def test_cancel_from_processing(self):
        sm = TaskStateMachine("t1")
        asyncio.run(sm.transition(TaskState.PROCESSING, trigger="start"))
        asyncio.run(sm.transition(TaskState.CANCELLED, trigger="user"))
        assert sm.state == TaskState.CANCELLED

    def test_hook_chain_executes(self):
        sm = TaskStateMachine("t1")
        events: list[tuple[TaskState, TaskState]] = []
        async def hook(sm, old, new):
            events.append((old, new))
        sm.add_hook(100, hook)
        asyncio.run(sm.transition(TaskState.PROCESSING, trigger="start"))
        assert events == [(TaskState.PENDING, TaskState.PROCESSING)]

    def test_to_dict_serialization(self):
        sm = TaskStateMachine("t1", metadata={"key": "value"})
        asyncio.run(sm.transition(TaskState.PROCESSING, trigger="start"))
        d = sm.to_dict()
        assert d["task_id"] == "t1"
        assert d["state"] == "processing"
        assert d["previous_state"] == "pending"
        assert d["metadata"]["key"] == "value"


class TestTaskLifecycleManager:
    @pytest.mark.asyncio
    async def test_submit_and_start(self):
        manager = TaskLifecycleManager()

        async def runner(task):
            task.result = "ok"

        manager.register_runner("echo", runner)
        task = manager.submit("echo", name="echo", payload={"msg": "hi"})
        await manager.start(task.task_id)
        await asyncio.sleep(0.01)
        t = manager.get_task(task.task_id)
        assert t is not None
        assert t.state_machine.state == TaskState.COMPLETED
        assert t.result == "ok"

    @pytest.mark.asyncio
    async def test_cancel_task(self):
        manager = TaskLifecycleManager()

        async def slow(task):
            await asyncio.sleep(0.1)
            task.result = "done"

        manager.register_runner("slow", slow)
        task = manager.submit("slow", name="slow")
        await manager.start(task.task_id)
        await asyncio.sleep(0.01)
        await manager.cancel(task.task_id)
        t = manager.get_task(task.task_id)
        assert t.state_machine.state == TaskState.CANCELLED

    @pytest.mark.asyncio
    async def test_list_tasks_by_state(self):
        manager = TaskLifecycleManager()
        manager.register_runner("noop", lambda task: None)
        manager.submit("noop", name="noop")
        manager.submit("noop", name="noop")
        pending = manager.list_tasks(TaskState.PENDING)
        assert len(pending) == 2

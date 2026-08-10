"""Tests for the multi-agent scheduler abstraction."""

from __future__ import annotations

import pytest

from app.core.scheduler_abstraction import (
    AgentInfo,
    AgentRole,
    InMemoryTaskChannel,
    MultiAgentScheduler,
    ScheduledTask,
    TaskState,
)


class TestInMemoryTaskChannel:
    @pytest.mark.asyncio
    async def test_send_and_receive(self) -> None:
        channel = InMemoryTaskChannel()
        await channel.send("agent-1", "agent-2", {"msg": "hello"})
        msg = await channel.receive("agent-2")
        assert msg is not None
        assert msg["msg"] == "hello"
        assert msg["sender_id"] == "agent-1"

    @pytest.mark.asyncio
    async def test_receive_empty_queue(self) -> None:
        channel = InMemoryTaskChannel()
        msg = await channel.receive("agent-1")
        assert msg is None

    @pytest.mark.asyncio
    async def test_broadcast(self) -> None:
        channel = InMemoryTaskChannel()
        await channel.broadcast("agent-1", {"msg": "broadcast"})
        broadcasts = await channel.get_broadcasts()
        assert len(broadcasts) == 1
        assert broadcasts[0]["msg"] == "broadcast"


class TestMultiAgentScheduler:
    @pytest.mark.asyncio
    async def test_register_agent(self) -> None:
        scheduler = MultiAgentScheduler()
        info = AgentInfo(agent_id="agent-1", role=AgentRole.WORKER)
        scheduler.register_agent(info)
        assert scheduler.get_agent("agent-1") is not None

    @pytest.mark.asyncio
    async def test_unregister_agent(self) -> None:
        scheduler = MultiAgentScheduler()
        scheduler.register_agent(AgentInfo(agent_id="agent-1", role=AgentRole.WORKER))
        assert scheduler.unregister_agent("agent-1")
        assert scheduler.get_agent("agent-1") is None

    @pytest.mark.asyncio
    async def test_list_agents_by_role(self) -> None:
        scheduler = MultiAgentScheduler()
        scheduler.register_agent(AgentInfo(agent_id="w1", role=AgentRole.WORKER))
        scheduler.register_agent(AgentInfo(agent_id="p1", role=AgentRole.PLANNER))
        workers = scheduler.list_agents(role=AgentRole.WORKER)
        assert len(workers) == 1
        assert workers[0].agent_id == "w1"

    @pytest.mark.asyncio
    async def test_submit_task(self) -> None:
        scheduler = MultiAgentScheduler()
        scheduler.register_agent(
            AgentInfo(
                agent_id="worker-1",
                role=AgentRole.WORKER,
                capabilities=["code", "test"],
            )
        )

        async def handler(desc: str, **kwargs) -> str:
            return f"Completed: {desc}"

        scheduler.register_task_handler("default", handler)
        task = await scheduler.submit_task("Test task")
        assert task.task_id
        assert task.state in (TaskState.PENDING, TaskState.RUNNING, TaskState.COMPLETED)

    @pytest.mark.asyncio
    async def test_wait_for_task(self) -> None:
        scheduler = MultiAgentScheduler()
        scheduler.register_agent(
            AgentInfo(agent_id="worker-1", role=AgentRole.WORKER)
        )

        async def handler(desc: str, **kwargs) -> str:
            return "done"

        scheduler.register_task_handler("default", handler)
        task = await scheduler.submit_task("Quick task")
        result = await scheduler.wait_for_task(task.task_id, timeout=5.0)
        assert result is not None
        assert result.state == TaskState.COMPLETED
        assert result.result == "done"

    @pytest.mark.asyncio
    async def test_cancel_task(self) -> None:
        scheduler = MultiAgentScheduler()
        scheduler.register_agent(
            AgentInfo(agent_id="worker-1", role=AgentRole.WORKER)
        )

        async def handler(desc: str, **kwargs) -> str:
            return "done"

        scheduler.register_task_handler("default", handler)
        task = await scheduler.submit_task("Cancel me")
        cancelled = await scheduler.cancel_task(task.task_id)
        assert cancelled
        assert task.state == TaskState.CANCELLED

    @pytest.mark.asyncio
    async def test_decompose_and_schedule(self) -> None:
        scheduler = MultiAgentScheduler()
        scheduler.register_agent(
            AgentInfo(agent_id="worker-1", role=AgentRole.WORKER)
        )

        async def handler(desc: str, **kwargs) -> str:
            return f"Done: {desc}"

        scheduler.register_task_handler("default", handler)
        parent, children = await scheduler.decompose_and_schedule(
            "Parent task",
            ["Sub 1", "Sub 2", "Sub 3"],
        )
        assert len(children) == 3
        assert len(parent.subtask_ids) == 3
        assert all(c.parent_task_id == parent.task_id for c in children)

    def test_get_scheduler_stats(self) -> None:
        scheduler = MultiAgentScheduler()
        scheduler.register_agent(AgentInfo(agent_id="a1", role=AgentRole.WORKER))
        stats = scheduler.get_scheduler_stats()
        assert stats["total_agents"] == 1
        assert stats["available_agents"] == 1

    def test_scheduled_task_duration(self) -> None:
        import time

        task = ScheduledTask(description="test")
        assert task.duration_ms == 0.0
        task.started_at = time.time() - 1.0
        task.completed_at = time.time()
        assert task.duration_ms > 0.0

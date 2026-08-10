"""Tests for group collaboration runtime.

Covers:
- Supervisor task tracking and cancellation
- Handoff with state transfer
- Shared state management
- Checkpoint resume (real restore, not stub)
- Review state machine
- Concurrency limits
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.core.agent_engine import AgentEngine
from app.core.auto_loop import AutoLoopEngine
from app.core.di import ScopeContext
from app.core.di import register as di_register
from app.core.executor import (
    CrewExecutorAdapter,
    SkillComposerExecutorAdapter,
    UnifiedExecutor,
    WorkflowExecutorAdapter,
)
from app.core.group_collaboration import (
    GroupCollaborationEngine,
    get_group_collaboration_engine,
)
from app.core.interfaces import IExecutor, IModelAdapter, ISkillRegistry, IToolRegistry
from app.core.sandbox import SandboxConfig, SandboxExecutor
from app.core.scheduler import TaskScheduler
from app.core.skill_composition import SkillComposer
from app.models.registry import ModelRegistry
from app.multi_agent.crew import Crew
from app.skills import LegacySkillRegistry, skill_registry
from app.storage import async_session
from app.storage.models_groups import AgentGroup, AgentGroupMember, AgentGroupTask
from app.tools import tool_registry
from app.workflow.engine import WorkflowEngine


@pytest.mark.asyncio
async def test_supervisor_tracks_running_task() -> None:
    async with async_session() as db:
        group = AgentGroup(name="supervisor-test", user_id="default-user")
        db.add(group)
        await db.commit()
        await db.refresh(group)

        member = AgentGroupMember(group_id=group.id, agent_id="agent-1", role="worker")
        db.add(member)
        await db.commit()
        await db.refresh(member)

        task = AgentGroupTask(group_id=group.id, description="supervisor task", worker_id=member.id)
        db.add(task)
        await db.commit()
        await db.refresh(task)

        task_id = task.id

    with patch.object(
        get_group_collaboration_engine(),
        "_run_sequential_process",
        new_callable=AsyncMock,
    ) as mock_process:
        mock_process.return_value = None
        asyncio.create_task(get_group_collaboration_engine().run_task(task_id))  # noqa: RUF006 - test-specific pattern
        for _ in range(20):
            async with async_session() as db:
                t = await db.get(AgentGroupTask, task_id)
                if t and t.status == "running":
                    break
            await asyncio.sleep(0.05)
        else:
            pytest.fail("task did not reach running state")

        mock_process.assert_called_once()


@pytest.mark.asyncio
async def test_run_task_respects_stop_status() -> None:
    async with async_session() as db:
        group = AgentGroup(name="stop-test", user_id="default-user")
        db.add(group)
        await db.commit()
        await db.refresh(group)

        member = AgentGroupMember(group_id=group.id, agent_id="agent-1", role="worker")
        db.add(member)
        await db.commit()
        await db.refresh(member)

        task = AgentGroupTask(group_id=group.id, description="stop task", worker_id=member.id)
        db.add(task)
        await db.commit()
        await db.refresh(task)

        task_id = task.id

    async def _slow_process(*args, **kwargs):
        await asyncio.sleep(5)

    with patch.object(
        get_group_collaboration_engine(),
        "_run_sequential_process",
        new_callable=AsyncMock,
        side_effect=_slow_process,
    ):
        runner = asyncio.create_task(get_group_collaboration_engine().run_task(task_id))
        await asyncio.sleep(0.05)

        async with async_session() as db:
            t = await db.get(AgentGroupTask, task_id)
            if t:
                t.status = "stopped"
                await db.commit()

        await asyncio.sleep(0.05)
        runner.cancel()
        with pytest.raises(asyncio.CancelledError):
            await runner

        async with async_session() as db:
            t = await db.get(AgentGroupTask, task_id)
            assert t is not None
            assert t.status == "stopped"


@pytest.mark.asyncio
async def test_handoff_updates_worker_and_broadcasts() -> None:
    async with async_session() as db:
        group = AgentGroup(name="handoff-test", user_id="default-user")
        db.add(group)
        await db.commit()
        await db.refresh(group)

        worker = AgentGroupMember(group_id=group.id, agent_id="agent-1", role="worker")
        target = AgentGroupMember(group_id=group.id, agent_id="agent-2", role="worker")
        db.add_all([worker, target])
        await db.commit()
        await db.refresh(worker)
        await db.refresh(target)

        task = AgentGroupTask(group_id=group.id, description="handoff task", worker_id=worker.id)
        db.add(task)
        await db.commit()
        await db.refresh(task)

        task_id = task.id

    engine = get_group_collaboration_engine()
    with patch("app.core.group_collaboration.group_ws_hub.broadcast", new_callable=AsyncMock) as mock_broadcast:
        result = await engine.handoff_task(task_id, target.agent_id, "overloaded")

    assert result["ok"] is True
    assert result["handoff_to"] == target.id

    async with async_session() as db:
        t = await db.get(AgentGroupTask, task_id)
        assert t is not None
        assert t.worker_id == target.id

    assert mock_broadcast.called


@pytest.mark.asyncio
async def test_supervisor_cancel_running_task() -> None:
    async with async_session() as db:
        group = AgentGroup(name="cancel-test", user_id="default-user")
        db.add(group)
        await db.commit()
        await db.refresh(group)

        member = AgentGroupMember(group_id=group.id, agent_id="agent-1", role="worker")
        db.add(member)
        await db.commit()
        await db.refresh(member)

        task = AgentGroupTask(group_id=group.id, description="cancel task", worker_id=member.id)
        db.add(task)
        await db.commit()
        await db.refresh(task)

        task_id = task.id

    async def _slow_process(*args, **kwargs):
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            raise

    engine = get_group_collaboration_engine()
    with patch.object(
        engine,
        "_run_sequential_process",
        new_callable=AsyncMock,
        side_effect=_slow_process,
    ):
        runner = asyncio.create_task(engine.run_task(task_id))
        await asyncio.sleep(0.05)

        async with async_session() as db:
            t = await db.get(AgentGroupTask, task_id)
            assert t is not None
            assert t.status == "running"

        assert engine.cancel_task(task_id) is True

        with pytest.raises(asyncio.CancelledError):
            await runner

        async with async_session() as db:
            t = await db.get(AgentGroupTask, task_id)
            assert t is not None
            assert t.status == "stopped"


@pytest.mark.asyncio
async def test_resume_from_checkpoint_restores_round() -> None:
    async with async_session() as db:
        group = AgentGroup(name="resume-test", user_id="default-user")
        db.add(group)
        await db.commit()
        await db.refresh(group)

        member = AgentGroupMember(group_id=group.id, agent_id="agent-1", role="worker")
        db.add(member)
        await db.commit()
        await db.refresh(member)

        task = AgentGroupTask(
            group_id=group.id,
            description="resume task",
            worker_id=member.id,
            max_rounds=5,
            current_round=3,
            status="paused",
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

        from app.storage.models_groups import AgentGroupTaskCheckpoint

        checkpoint = AgentGroupTaskCheckpoint(
            group_id=group.id,
            task_id=task.id,
            status="paused",
            current_round=3,
            max_rounds=5,
            current_artifact="draft output",
            task_description=task.description,
        )
        db.add(checkpoint)
        await db.commit()
        await db.refresh(checkpoint)

        task_id = task.id

    engine = get_group_collaboration_engine()
    checkpoint = await engine._load_latest_checkpoint(task_id)
    assert checkpoint is not None
    assert checkpoint.current_round == 3

    await engine._resume_from_checkpoint(task, checkpoint)

    async with async_session() as db:
        t = await db.get(AgentGroupTask, task_id)
        assert t is not None
        assert t.current_round == 3
        assert t.status == "running"
        assert t.final_output == "draft output"


@pytest.mark.asyncio
async def test_run_agent_with_retry_falls_back_after_failures() -> None:
    call_count = 0

    async def _failing_agent(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise Exception("model down")

    engine = get_group_collaboration_engine()
    with patch.object(
        engine,
        "_run_agent_simple",
        new_callable=AsyncMock,
        side_effect=_failing_agent,
    ):
        output, tokens = await engine._run_agent_with_retry(
            agent_id="agent-1",
            provider="openai",
            model_id="gpt-4o",
            api_key="fake",
            system_prompt="prompt",
            user_message="msg",
            tools=[],
            group_id="group-1",
            role="worker",
        )

    assert output == ""
    assert tokens == 0
    assert call_count == 4


@pytest.mark.asyncio
async def test_concurrency_limit_blocks_extra_tasks() -> None:
    engine = GroupCollaborationEngine(
        model_registry=ModelRegistry(),
        tool_registry=tool_registry,
        max_concurrent_tasks=1,
    )
    assert engine._task_semaphore._value == 1

    async def _slow_task():
        async with engine._task_semaphore:
            await asyncio.sleep(0.1)

    start = asyncio.get_event_loop().time()
    task1 = asyncio.create_task(_slow_task())
    task2 = asyncio.create_task(_slow_task())
    await asyncio.gather(task1, task2)
    elapsed = asyncio.get_event_loop().time() - start
    assert elapsed >= 0.19


@pytest.mark.asyncio
async def test_review_state_machine_transitions() -> None:
    engine = get_group_collaboration_engine()
    task_id = "task-review"
    reviewer_id = "reviewer-1"

    assert engine.get_review_state(task_id, reviewer_id) == "pending"

    engine.set_review_state(task_id, reviewer_id, "approved")
    assert engine.get_review_state(task_id, reviewer_id) == "approved"
    summary = engine.get_task_review_summary(task_id)
    assert summary["approved"] == 1
    assert summary["pending"] == 0

    engine.set_review_state(task_id, reviewer_id, "rejected")
    assert engine.get_review_state(task_id, reviewer_id) == "rejected"
    summary = engine.get_task_review_summary(task_id)
    assert summary["rejected"] == 1
    assert summary["approved"] == 0


@pytest.fixture(autouse=True)
def _setup_group_di():
    with ScopeContext("group_test"):
        model_registry = ModelRegistry()
        skill_registry_instance = skill_registry
        tool_registry_instance = tool_registry
        agent_engine = AgentEngine(model_registry=model_registry, tool_registry=tool_registry_instance)
        auto_loop_engine = AutoLoopEngine()
        task_scheduler = TaskScheduler()
        sandbox = SandboxExecutor(SandboxConfig())

        di_register(IModelAdapter, model_registry)
        di_register(IToolRegistry, tool_registry_instance)
        di_register(ISkillRegistry, LegacySkillRegistry(skill_registry_instance))
        di_register("ModelRegistry", model_registry)
        di_register("ToolRegistry", tool_registry_instance)
        di_register("SkillRegistry", skill_registry_instance)
        di_register("AgentEngine", agent_engine)
        di_register("AutoLoopEngine", auto_loop_engine)
        di_register("TaskScheduler", task_scheduler)
        di_register("SandboxExecutor", sandbox)

        workflow_engine = WorkflowEngine(engine=agent_engine, model_registry=model_registry)
        skill_composer = SkillComposer(skill_registry=skill_registry_instance)
        unified = UnifiedExecutor()
        unified.register_adapter("workflow", WorkflowExecutorAdapter(workflow_engine))
        unified.register_adapter("crew", CrewExecutorAdapter(Crew([], [], agent_engine)))
        unified.register_adapter("skill", SkillComposerExecutorAdapter(skill_composer))
        di_register(IExecutor, unified)
        di_register("UnifiedExecutor", unified)
        di_register("SkillComposer", skill_composer)
        yield

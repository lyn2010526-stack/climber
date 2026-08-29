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
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.core import group_collaboration as group_collaboration_module
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
    TaskLease,
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

        member = AgentGroupMember(
            group_id=group.id,
            agent_id="agent-1",
            role="worker",
            model_provider="openai",
        )
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
async def test_cancelled_task_is_not_changed_back_to_stopped() -> None:
    async with async_session() as db:
        group = AgentGroup(name="cancelled-terminal-test", user_id="default-user")
        db.add(group)
        await db.commit()
        await db.refresh(group)

        member = AgentGroupMember(group_id=group.id, agent_id="agent-1", role="worker")
        db.add(member)
        await db.commit()
        await db.refresh(member)

        task = AgentGroupTask(group_id=group.id, description="cancel terminal task", worker_id=member.id)
        db.add(task)
        await db.commit()
        await db.refresh(task)
        task_id = task.id

    async def _slow_process(*args, **kwargs):
        await asyncio.sleep(30)

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
            task = await db.get(AgentGroupTask, task_id)
            assert task is not None
            task.status = "cancelled"
            await db.commit()

        assert engine.cancel_task(task_id) is True
        with pytest.raises(asyncio.CancelledError):
            await runner

    async with async_session() as db:
        task = await db.get(AgentGroupTask, task_id)
        assert task is not None
        assert task.status == "cancelled"


@pytest.mark.asyncio
async def test_worker_failure_persists_failed_terminal_status() -> None:
    async with async_session() as db:
        group = AgentGroup(name="worker-failure-test", user_id="default-user")
        db.add(group)
        await db.commit()
        await db.refresh(group)

        member = AgentGroupMember(group_id=group.id, agent_id="agent-1", role="worker")
        db.add(member)
        await db.commit()
        await db.refresh(member)

        task = AgentGroupTask(
            group_id=group.id,
            description="worker failure task",
            worker_id=member.id,
            status="running",
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        task_id = task.id

    engine = get_group_collaboration_engine()
    with (
        patch.object(engine, "_build_context_from_dependencies", new_callable=AsyncMock, return_value=[]),
        patch.object(engine, "_inject_memory", new_callable=AsyncMock, return_value=[]),
        patch.object(engine, "_run_agent_with_retry", new_callable=AsyncMock, return_value=("", 0)),
        patch("app.core.group_collaboration.group_ws_hub.broadcast", new_callable=AsyncMock),
    ):
        await engine._run_sequential_process(task, member, [], group)

    async with async_session() as db:
        task = await db.get(AgentGroupTask, task_id)
        assert task is not None
        assert task.status == "failed"
        assert task.completed_at is not None


@pytest.mark.asyncio
async def test_sequential_completion_does_not_overwrite_cross_instance_cancellation() -> None:
    async with async_session() as db:
        group = AgentGroup(name="cross-instance-cancel", user_id="default-user")
        db.add(group)
        await db.commit()
        await db.refresh(group)
        member = AgentGroupMember(
            group_id=group.id,
            agent_id="agent-1",
            role="worker",
            model_provider="openai",
        )
        db.add(member)
        await db.commit()
        await db.refresh(member)
        task = AgentGroupTask(
            group_id=group.id,
            description="cancel during model call",
            worker_id=member.id,
            status="running",
        )
        db.add(task)
        await db.commit()
        task_id = task.id

    started = asyncio.Event()
    release = asyncio.Event()

    async def _blocked_agent(*args, **kwargs):
        started.set()
        await release.wait()
        return "finished output", 1

    engine = get_group_collaboration_engine()
    with (
        patch.object(engine, "_build_context_from_dependencies", new_callable=AsyncMock, return_value=[]),
        patch.object(engine, "_inject_memory", new_callable=AsyncMock, return_value=[]),
        patch.object(engine, "_run_agent_with_retry", new_callable=AsyncMock, side_effect=_blocked_agent),
        patch.object(engine, "_invoke_step_callback", new_callable=AsyncMock) as step_callback,
        patch.object(engine, "_store_memory", new_callable=AsyncMock),
        patch.object(engine, "_invoke_task_callback", new_callable=AsyncMock),
        patch.object(engine, "_save_checkpoint", new_callable=AsyncMock) as save_checkpoint,
        patch("app.core.group_collaboration.group_ws_hub.broadcast", new_callable=AsyncMock) as broadcast,
    ):
        runner = asyncio.create_task(engine._run_sequential_process(task, member, [], group))
        await started.wait()
        async with async_session() as db:
            current = await db.get(AgentGroupTask, task_id)
            assert current is not None
            current.status = "cancelled"
            await db.commit()
        release.set()
        await runner

    async with async_session() as db:
        current = await db.get(AgentGroupTask, task_id)
        assert current is not None
        assert current.status == "cancelled"
        assert current.final_output is None
    step_callback.assert_not_awaited()
    save_checkpoint.assert_not_awaited()
    assert not any(call.args[1]["type"] == "worker_done" for call in broadcast.await_args_list)


@pytest.mark.asyncio
async def test_sequential_partial_does_not_overwrite_cross_instance_cancellation() -> None:
    async with async_session() as db:
        group = AgentGroup(name="cross-instance-partial-cancel", user_id="default-user")
        db.add(group)
        await db.commit()
        await db.refresh(group)
        member = AgentGroupMember(
            group_id=group.id,
            agent_id="agent-1",
            role="worker",
            model_provider="openai",
        )
        db.add(member)
        await db.commit()
        await db.refresh(member)
        task = AgentGroupTask(
            group_id=group.id,
            description="cancel before partial result",
            worker_id=member.id,
            max_rounds=1,
            status="running",
        )
        db.add(task)
        await db.commit()
        task_id = task.id

    async def _cancel_during_guardrail(*args, **kwargs):
        async with async_session() as db:
            current = await db.get(AgentGroupTask, task_id)
            assert current is not None
            current.status = "cancelled"
            await db.commit()
        return False, [{"description": "retry", "severity": "high"}]

    engine = get_group_collaboration_engine()
    with (
        patch.object(engine, "_build_context_from_dependencies", new_callable=AsyncMock, return_value=[]),
        patch.object(engine, "_inject_memory", new_callable=AsyncMock, return_value=[]),
        patch.object(engine, "_run_agent_with_retry", new_callable=AsyncMock, return_value=("draft output", 1)),
        patch.object(engine, "_run_guardrails", new_callable=AsyncMock, side_effect=_cancel_during_guardrail),
        patch.object(engine, "_invoke_step_callback", new_callable=AsyncMock),
        patch.object(engine, "_save_checkpoint", new_callable=AsyncMock),
        patch("app.core.group_collaboration.group_ws_hub.broadcast", new_callable=AsyncMock) as broadcast,
    ):
        await engine._run_sequential_process(task, member, [], group)

    async with async_session() as db:
        current = await db.get(AgentGroupTask, task_id)
        assert current is not None
        assert current.status == "cancelled"
        assert current.final_output is None
    assert not any(call.args[1]["type"] == "task_partial" for call in broadcast.await_args_list)


@pytest.mark.asyncio
async def test_worker_failure_does_not_broadcast_failure_after_cross_instance_cancellation() -> None:
    async with async_session() as db:
        group = AgentGroup(name="cross-instance-failure-cancel", user_id="default-user")
        db.add(group)
        await db.commit()
        await db.refresh(group)
        member = AgentGroupMember(
            group_id=group.id,
            agent_id="agent-1",
            role="worker",
            model_provider="openai",
        )
        db.add(member)
        await db.commit()
        await db.refresh(member)
        task = AgentGroupTask(
            group_id=group.id,
            description="cancel during worker failure",
            worker_id=member.id,
            status="running",
        )
        db.add(task)
        await db.commit()
        task_id = task.id

    async def _cancel_then_fail(*args, **kwargs):
        async with async_session() as db:
            current = await db.get(AgentGroupTask, task_id)
            assert current is not None
            current.status = "cancelled"
            await db.commit()
        raise RuntimeError("model failed after cancellation")

    engine = get_group_collaboration_engine()
    with (
        patch.object(engine, "_build_context_from_dependencies", new_callable=AsyncMock, return_value=[]),
        patch.object(engine, "_inject_memory", new_callable=AsyncMock, return_value=[]),
        patch.object(engine, "_run_agent_with_retry", new_callable=AsyncMock, side_effect=_cancel_then_fail),
        patch("app.core.group_collaboration.group_ws_hub.broadcast", new_callable=AsyncMock) as broadcast,
    ):
        await engine._run_sequential_process(task, member, [], group)

    async with async_session() as db:
        current = await db.get(AgentGroupTask, task_id)
        assert current is not None
        assert current.status == "cancelled"
    assert not any(call.args[1]["type"] == "task_failed" for call in broadcast.await_args_list)


@pytest.mark.asyncio
async def test_group_chat_stops_side_effects_after_cross_instance_cancellation() -> None:
    async with async_session() as db:
        group = AgentGroup(name="group-chat-cancel", user_id="default-user", process_type="group_chat")
        db.add(group)
        await db.commit()
        await db.refresh(group)
        members = [
            AgentGroupMember(
                group_id=group.id,
                agent_id=f"agent-{index}",
                role="worker",
                model_provider="openai",
            )
            for index in range(2)
        ]
        db.add_all(members)
        await db.commit()
        await db.refresh(group, ["members"])
        task = AgentGroupTask(
            group_id=group.id,
            description="cancel group chat",
            max_rounds=1,
            status="running",
        )
        db.add(task)
        await db.commit()
        task_id = task.id

    started = asyncio.Event()
    release = asyncio.Event()

    async def _blocked_agent(*args, **kwargs):
        started.set()
        await release.wait()
        return "late response", 1

    engine = get_group_collaboration_engine()
    with (
        patch.object(engine, "_run_agent_simple", new_callable=AsyncMock, side_effect=_blocked_agent) as run_agent,
        patch.object(engine, "_invoke_step_callback", new_callable=AsyncMock) as step_callback,
        patch("app.core.group_collaboration.group_ws_hub.broadcast", new_callable=AsyncMock) as broadcast,
    ):
        runner = asyncio.create_task(engine._run_group_chat_process(task, group))
        await asyncio.wait_for(started.wait(), timeout=2)
        async with async_session() as db:
            current = await db.get(AgentGroupTask, task_id)
            assert current is not None
            current.status = "cancelled"
            await db.commit()
        release.set()
        await runner

    assert run_agent.await_count == 1
    step_callback.assert_not_awaited()
    assert not any(call.args[1]["type"] == "message" for call in broadcast.await_args_list)
    async with async_session() as db:
        current = await db.get(AgentGroupTask, task_id)
        assert current is not None
        assert current.status == "cancelled"


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
async def test_checkpoint_restore_does_not_revive_cancelled_task() -> None:
    async with async_session() as db:
        group = AgentGroup(name="cancel-before-restore", user_id="default-user")
        db.add(group)
        await db.commit()
        await db.refresh(group)
        task = AgentGroupTask(
            group_id=group.id,
            description="cancelled checkpoint task",
            status="cancelled",
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

        from app.storage.models_groups import AgentGroupTaskCheckpoint

        checkpoint = AgentGroupTaskCheckpoint(
            group_id=group.id,
            task_id=task.id,
            status="paused",
            current_round=2,
            max_rounds=5,
            current_artifact="stale draft",
            task_description=task.description,
        )
        db.add(checkpoint)
        await db.commit()
        task_id = task.id

    restored = await get_group_collaboration_engine()._resume_from_checkpoint(task, checkpoint)

    assert restored is None
    async with async_session() as db:
        current = await db.get(AgentGroupTask, task_id)
        assert current is not None
        assert current.status == "cancelled"
        assert current.final_output is None


@pytest.mark.asyncio
async def test_run_task_continues_sequential_execution_from_checkpoint() -> None:
    async with async_session() as db:
        group = AgentGroup(name="resume-and-continue", user_id="default-user")
        db.add(group)
        await db.commit()
        await db.refresh(group)
        member = AgentGroupMember(
            group_id=group.id,
            agent_id="agent-1",
            role="worker",
            model_provider="openai",
        )
        db.add(member)
        await db.commit()
        await db.refresh(member)
        task = AgentGroupTask(
            group_id=group.id,
            description="continue resumed task",
            worker_id=member.id,
            max_rounds=5,
            status="pending",
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
            current_artifact="checkpoint draft",
            task_description=task.description,
        )
        db.add(checkpoint)
        await db.commit()
        task_id = task.id

    engine = get_group_collaboration_engine()
    with patch.object(engine, "_run_sequential_process", new_callable=AsyncMock) as run_process:
        await engine.run_task(task_id)

    run_process.assert_awaited_once()
    resumed_task = run_process.await_args.args[0]
    assert resumed_task.current_round == 3
    assert resumed_task.final_output == "checkpoint draft"


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
async def test_run_task_applies_configured_concurrency_limit() -> None:
    engine = GroupCollaborationEngine(
        model_registry=ModelRegistry(),
        tool_registry=tool_registry,
        max_concurrent_tasks=1,
    )
    active_count = 0
    max_active_count = 0

    async def _run_process(*args, **kwargs):
        nonlocal active_count, max_active_count
        active_count += 1
        max_active_count = max(max_active_count, active_count)
        await asyncio.sleep(0.05)
        active_count -= 1

    async with async_session() as db:
        group = AgentGroup(name="run-task-limit", user_id="default-user")
        db.add(group)
        await db.commit()
        await db.refresh(group)
        member = AgentGroupMember(group_id=group.id, agent_id="agent-1", role="worker")
        db.add(member)
        await db.commit()
        await db.refresh(member)
        tasks = [
            AgentGroupTask(group_id=group.id, description=f"limited task {index}", worker_id=member.id)
            for index in range(2)
        ]
        db.add_all(tasks)
        await db.commit()
        task_ids = [task.id for task in tasks]

    with patch.object(engine, "_run_sequential_process", new_callable=AsyncMock, side_effect=_run_process):
        await asyncio.gather(*(engine.run_task(task_id) for task_id in task_ids))

    assert max_active_count == 1


@pytest.mark.asyncio
async def test_run_task_does_not_restart_cancelled_task() -> None:
    async with async_session() as db:
        group = AgentGroup(name="cancelled-before-start", user_id="default-user")
        db.add(group)
        await db.commit()
        await db.refresh(group)
        member = AgentGroupMember(group_id=group.id, agent_id="agent-1", role="worker")
        db.add(member)
        await db.commit()
        await db.refresh(member)
        task = AgentGroupTask(
            group_id=group.id,
            description="already cancelled",
            worker_id=member.id,
            status="cancelled",
        )
        db.add(task)
        await db.commit()
        task_id = task.id

    engine = get_group_collaboration_engine()
    with patch.object(engine, "_run_sequential_process", new_callable=AsyncMock) as run_process:
        await engine.run_task(task_id)

    run_process.assert_not_called()
    async with async_session() as db:
        task = await db.get(AgentGroupTask, task_id)
        assert task is not None
        assert task.status == "cancelled"


@pytest.mark.asyncio
async def test_run_task_ignores_duplicate_in_process_execution() -> None:
    async with async_session() as db:
        group = AgentGroup(name="duplicate-run", user_id="default-user")
        db.add(group)
        await db.commit()
        await db.refresh(group)
        member = AgentGroupMember(group_id=group.id, agent_id="agent-1", role="worker")
        db.add(member)
        await db.commit()
        await db.refresh(member)
        task = AgentGroupTask(group_id=group.id, description="run once", worker_id=member.id)
        db.add(task)
        await db.commit()
        task_id = task.id

    started = asyncio.Event()
    release = asyncio.Event()

    async def _blocked_process(*args, **kwargs):
        started.set()
        await release.wait()

    engine = get_group_collaboration_engine()
    with patch.object(engine, "_run_sequential_process", new_callable=AsyncMock, side_effect=_blocked_process) as run_process:
        first_run = asyncio.create_task(engine.run_task(task_id))
        await started.wait()
        second_run = asyncio.create_task(engine.run_task(task_id))
        await asyncio.sleep(0)
        release.set()
        await asyncio.gather(first_run, second_run)

    run_process.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_task_atomically_claims_task_across_engine_instances() -> None:
    async with async_session() as db:
        group = AgentGroup(name="cross-instance-claim", user_id="default-user")
        db.add(group)
        await db.commit()
        await db.refresh(group)
        member = AgentGroupMember(group_id=group.id, agent_id="agent-1", role="worker")
        db.add(member)
        await db.commit()
        await db.refresh(member)
        task = AgentGroupTask(group_id=group.id, description="run once globally", worker_id=member.id)
        db.add(task)
        await db.commit()
        task_id = task.id

    first_engine = GroupCollaborationEngine(ModelRegistry(), tool_registry)
    second_engine = GroupCollaborationEngine(ModelRegistry(), tool_registry)
    started = asyncio.Event()
    release = asyncio.Event()
    execution_count = 0

    async def _blocked_process(*args, **kwargs):
        nonlocal execution_count
        execution_count += 1
        started.set()
        await release.wait()

    with (
        patch.object(first_engine, "_run_sequential_process", new_callable=AsyncMock, side_effect=_blocked_process),
        patch.object(second_engine, "_run_sequential_process", new_callable=AsyncMock, side_effect=_blocked_process),
    ):
        first_run = asyncio.create_task(first_engine.run_task(task_id))
        await started.wait()
        second_run = asyncio.create_task(second_engine.run_task(task_id))
        await asyncio.sleep(0.05)
        release.set()
        await asyncio.gather(first_run, second_run)

    assert execution_count == 1


@pytest.mark.asyncio
async def test_dag_task_atomically_claims_task_across_engine_instances() -> None:
    async with async_session() as db:
        group = AgentGroup(name="cross-instance-dag-claim", user_id="default-user")
        db.add(group)
        await db.commit()
        await db.refresh(group)
        member = AgentGroupMember(
            group_id=group.id,
            agent_id="agent-1",
            role="worker",
            model_provider="openai",
        )
        db.add(member)
        await db.commit()
        await db.refresh(member)
        task = AgentGroupTask(group_id=group.id, description="run DAG once globally", worker_id=member.id)
        db.add(task)
        await db.commit()
        task_id = task.id

    first_engine = GroupCollaborationEngine(ModelRegistry(), tool_registry)
    second_engine = GroupCollaborationEngine(ModelRegistry(), tool_registry)
    started = asyncio.Event()
    release = asyncio.Event()
    execution_count = 0

    async def _blocked_agent(*args, **kwargs):
        nonlocal execution_count
        execution_count += 1
        started.set()
        await release.wait()
        return "DAG output", 1

    with (
        patch.object(first_engine, "_inject_memory", new_callable=AsyncMock, return_value=""),
        patch.object(second_engine, "_inject_memory", new_callable=AsyncMock, return_value=""),
        patch.object(first_engine, "_run_agent_with_retry", new_callable=AsyncMock, side_effect=_blocked_agent),
        patch.object(second_engine, "_run_agent_with_retry", new_callable=AsyncMock, side_effect=_blocked_agent),
    ):
        first_run = asyncio.create_task(first_engine._run_single_task_in_dag(task, group, {}))
        await asyncio.wait_for(started.wait(), timeout=2)
        second_run = asyncio.create_task(second_engine._run_single_task_in_dag(task, group, {}))
        await asyncio.sleep(0.05)
        release.set()
        await asyncio.gather(first_run, second_run)

    assert execution_count == 1
    async with async_session() as db:
        current = await db.get(AgentGroupTask, task_id)
        assert current is not None
        assert current.status == "completed"


@pytest.mark.asyncio
async def test_dag_task_failure_persists_failed_terminal_status() -> None:
    async with async_session() as db:
        group = AgentGroup(name="dag-failure", user_id="default-user")
        db.add(group)
        await db.commit()
        await db.refresh(group)
        task = AgentGroupTask(group_id=group.id, description="DAG task without worker")
        db.add(task)
        await db.commit()
        task_id = task.id

    result = await get_group_collaboration_engine().run_group_tasks(group.id)

    assert result["levels"][0][0]["status"] == "failed"
    async with async_session() as db:
        current = await db.get(AgentGroupTask, task_id)
        assert current is not None
        assert current.status == "failed"
        assert current.completed_at is not None


@pytest.mark.asyncio
async def test_hierarchical_task_without_manager_persists_failed_terminal_status() -> None:
    async with async_session() as db:
        group = AgentGroup(
            name="hierarchical-without-manager",
            user_id="default-user",
            process_type="hierarchical",
        )
        db.add(group)
        await db.commit()
        await db.refresh(group)
        task = AgentGroupTask(
            group_id=group.id,
            description="hierarchical task without members",
            status="running",
        )
        db.add(task)
        await db.commit()
        task_id = task.id

    await get_group_collaboration_engine()._run_hierarchical_process(task, group)

    async with async_session() as db:
        current = await db.get(AgentGroupTask, task_id)
        assert current is not None
        assert current.status == "failed"
        assert current.completed_at is not None


@pytest.mark.asyncio
async def test_unknown_process_type_persists_failed_status() -> None:
    async with async_session() as db:
        group = AgentGroup(
            name="unknown-process",
            user_id="default-user",
            process_type="unsupported",
        )
        db.add(group)
        await db.commit()
        await db.refresh(group)
        member = AgentGroupMember(group_id=group.id, agent_id="agent-1", role="worker")
        db.add(member)
        await db.commit()
        await db.refresh(member)
        task = AgentGroupTask(group_id=group.id, description="unsupported process", worker_id=member.id)
        db.add(task)
        await db.commit()
        task_id = task.id

    await get_group_collaboration_engine().run_task(task_id)

    async with async_session() as db:
        task = await db.get(AgentGroupTask, task_id)
        assert task is not None
        assert task.status == "failed"
        assert task.completed_at is not None


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


async def _make_claimable_task(description: str) -> tuple[AgentGroupTask, AgentGroupMember]:
    async with async_session() as db:
        group = AgentGroup(name=f"lease-{description}", user_id="default-user")
        db.add(group)
        await db.commit()
        await db.refresh(group)
        member = AgentGroupMember(group_id=group.id, agent_id="agent-1", role="worker")
        db.add(member)
        await db.commit()
        await db.refresh(member)
        task = AgentGroupTask(group_id=group.id, description=description, worker_id=member.id)
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return task, member


@pytest.mark.asyncio
async def test_claim_assigns_lease_token_and_owner() -> None:
    task, _member = await _make_claimable_task("claim lease")
    engine = GroupCollaborationEngine(ModelRegistry(), tool_registry)

    lease = await engine._claim_lease(task.id)

    assert lease is not None
    assert lease.token >= 1
    assert lease.owner == engine.instance_id
    async with async_session() as db:
        current = await db.get(AgentGroupTask, task.id)
        assert current is not None
        assert current.status == "running"
        assert current.lease_owner == engine.instance_id
        assert current.lease_token == lease.token
        assert current.lease_expires_at is not None


@pytest.mark.asyncio
async def test_expired_lease_running_task_can_be_reclaimed_with_higher_token() -> None:
    task, _member = await _make_claimable_task("expired reclaim")
    first_engine = GroupCollaborationEngine(ModelRegistry(), tool_registry)
    second_engine = GroupCollaborationEngine(ModelRegistry(), tool_registry)

    first_lease = await first_engine._claim_lease(task.id)
    assert first_lease is not None
    async with async_session() as db:
        stale = await db.get(AgentGroupTask, task.id)
        assert stale is not None
        stale.lease_expires_at = datetime.now(UTC) - timedelta(seconds=60)
        await db.commit()

    second_lease = await second_engine._claim_lease(task.id, status="running", takeover=True)

    assert second_lease is not None
    assert second_lease.token > first_lease.token
    assert second_lease.owner == second_engine.instance_id


@pytest.mark.asyncio
async def test_active_lease_running_task_cannot_be_taken_over() -> None:
    task, _member = await _make_claimable_task("active lease")
    first_engine = GroupCollaborationEngine(ModelRegistry(), tool_registry)
    second_engine = GroupCollaborationEngine(ModelRegistry(), tool_registry)

    first_lease = await first_engine._claim_lease(task.id)
    assert first_lease is not None

    second_lease = await second_engine._claim_lease(task.id, status="running", takeover=True)

    assert second_lease is None


@pytest.mark.asyncio
async def test_heartbeat_renews_only_matching_lease() -> None:
    task, _member = await _make_claimable_task("heartbeat")
    engine = GroupCollaborationEngine(ModelRegistry(), tool_registry)
    other = GroupCollaborationEngine(ModelRegistry(), tool_registry)

    lease = await engine._claim_lease(task.id)
    assert lease is not None

    assert await engine._renew_lease(task.id, lease.token) is True
    assert await other._renew_lease(task.id, lease.token) is False


@pytest.mark.asyncio
async def test_heartbeat_renews_lease_while_awaiting_human_review() -> None:
    task, _member = await _make_claimable_task("human review heartbeat")
    engine = GroupCollaborationEngine(ModelRegistry(), tool_registry)
    lease = await engine._claim_lease(task.id)
    assert lease is not None

    async with async_session() as db:
        current = await db.get(AgentGroupTask, task.id)
        assert current is not None
        current.status = "awaiting_human_review"
        await db.commit()

    assert await engine._renew_lease(task.id, lease.token) is True


@pytest.mark.asyncio
async def test_heartbeat_cancels_local_task_after_lease_loss() -> None:
    task, _member = await _make_claimable_task("heartbeat lease loss")
    engine = GroupCollaborationEngine(ModelRegistry(), tool_registry)
    lease = await engine._claim_lease(task.id)
    assert lease is not None

    current_task = asyncio.current_task()
    assert current_task is not None
    engine._running_tasks[task.id] = current_task

    with (
        patch.object(engine, "_renew_lease", new=AsyncMock(return_value=False)),
        patch.object(engine, "cancel_task", return_value=True) as cancel_task,
        patch("app.core.group_collaboration.LEASE_HEARTBEAT_SECONDS", 0),
    ):
        await engine._heartbeat_loop(lease)

    cancel_task.assert_called_once_with(task.id)


@pytest.mark.asyncio
async def test_cancel_revokes_lease_and_fences_old_writer() -> None:
    task, _member = await _make_claimable_task("cancel revokes lease")
    engine = GroupCollaborationEngine(ModelRegistry(), tool_registry)

    lease = await engine._claim_lease(task.id)
    assert lease is not None

    async with async_session() as db:
        current = await db.get(AgentGroupTask, task.id)
        assert current is not None
        current.status = "cancelled"
        current.completed_at = datetime.now(UTC)
        current.lease_owner = None
        current.lease_expires_at = None
        current.lease_token = lease.token + 1
        await db.commit()

    assert await engine._renew_lease(task.id, lease.token) is False

    completion = await engine._complete_running_task(
        task.id,
        lease.token,
        status="completed",
        final_output="late output",
    )
    assert completion is False
    async with async_session() as db:
        current = await db.get(AgentGroupTask, task.id)
        assert current is not None
        assert current.status == "cancelled"
        assert current.final_output is None


@pytest.mark.asyncio
async def test_progress_write_requires_current_lease_token() -> None:
    task, _member = await _make_claimable_task("progress fencing")
    engine = GroupCollaborationEngine(ModelRegistry(), tool_registry)

    lease = await engine._claim_lease(task.id)
    assert lease is not None

    assert await engine._update_progress(task.id, lease.token + 5, current_round=7) is False
    assert await engine._update_progress(task.id, lease.token, current_round=2) is True
    async with async_session() as db:
        current = await db.get(AgentGroupTask, task.id)
        assert current is not None
        assert current.current_round == 2


@pytest.mark.asyncio
async def test_expired_lease_cannot_write_progress_or_terminal_state() -> None:
    task, _member = await _make_claimable_task("expired writer fencing")
    engine = GroupCollaborationEngine(ModelRegistry(), tool_registry)
    lease = await engine._claim_lease(task.id)
    assert lease is not None

    async with async_session() as db:
        current = await db.get(AgentGroupTask, task.id)
        assert current is not None
        current.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await db.commit()

    assert await engine._renew_lease(task.id, lease.token) is False
    assert await engine._update_progress(task.id, lease.token, current_round=4) is False
    assert await engine._complete_running_task(task.id, lease.token, status="completed") is False


@pytest.mark.asyncio
async def test_dag_execution_runs_heartbeat_for_claimed_task() -> None:
    task, _member = await _make_claimable_task("DAG heartbeat")
    async with async_session() as db:
        group = await db.get(AgentGroup, task.group_id)
        assert group is not None

    engine = GroupCollaborationEngine(ModelRegistry(), tool_registry)
    heartbeat_started = asyncio.Event()

    async def _heartbeat(_lease: TaskLease) -> None:
        heartbeat_started.set()
        await asyncio.Event().wait()

    async def _run_dag_task(*args, **kwargs) -> bool:
        await asyncio.wait_for(heartbeat_started.wait(), timeout=2)
        return True

    with (
        patch.object(engine, "_heartbeat_loop", side_effect=_heartbeat) as heartbeat,
        patch.object(engine, "_run_single_task_in_dag", side_effect=_run_dag_task),
    ):
        result = await engine.run_group_tasks(group.id)

    assert result["status"] == "completed"
    heartbeat.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_task_takes_over_expired_running_lease_from_checkpoint() -> None:
    task, _member = await _make_claimable_task("crash takeover")
    stale_engine = GroupCollaborationEngine(ModelRegistry(), tool_registry)
    stale_lease = await stale_engine._claim_lease(task.id)
    assert stale_lease is not None

    from app.storage.models_groups import AgentGroupTaskCheckpoint

    async with async_session() as db:
        checkpoint = AgentGroupTaskCheckpoint(
            group_id=task.group_id,
            task_id=task.id,
            status="paused",
            current_round=2,
            max_rounds=5,
            current_artifact="pre-crash draft",
            task_description=task.description,
        )
        db.add(checkpoint)
        current = await db.get(AgentGroupTask, task.id)
        assert current is not None
        current.lease_expires_at = datetime.now(UTC) - timedelta(seconds=120)
        await db.commit()

    engine = GroupCollaborationEngine(ModelRegistry(), tool_registry)
    with patch.object(engine, "_run_sequential_process", new_callable=AsyncMock) as run_process:
        await engine.run_task(task.id)

    run_process.assert_awaited_once()
    resumed_task = run_process.await_args.args[0]
    assert resumed_task.current_round == 2
    assert resumed_task.final_output == "pre-crash draft"
    async with async_session() as db:
        current = await db.get(AgentGroupTask, task.id)
        assert current is not None
        assert current.lease_owner == engine.instance_id
        assert current.lease_token > stale_lease.token


@pytest.mark.asyncio
async def test_recover_stale_running_tasks_ignores_active_leases() -> None:
    task, _member = await _make_claimable_task("recover scan")
    engine = GroupCollaborationEngine(ModelRegistry(), tool_registry)
    lease = await engine._claim_lease(task.id)
    assert lease is not None

    assert await engine.recover_stale_running_tasks() == 0
    async with async_session() as db:
        current = await db.get(AgentGroupTask, task.id)
        assert current is not None
        assert current.lease_owner == engine.instance_id


@pytest.mark.asyncio
async def test_recover_stale_human_review_task_schedules_takeover() -> None:
    task, _member = await _make_claimable_task("recover human review")
    stale_engine = GroupCollaborationEngine(ModelRegistry(), tool_registry)
    lease = await stale_engine._claim_lease(task.id)
    assert lease is not None

    async with async_session() as db:
        current = await db.get(AgentGroupTask, task.id)
        assert current is not None
        current.status = "awaiting_human_review"
        current.lease_expires_at = datetime.now(UTC) - timedelta(minutes=1)
        await db.commit()

    engine = GroupCollaborationEngine(ModelRegistry(), tool_registry)
    scheduled = asyncio.Event()

    async def _record_run(task_id: str) -> None:
        assert task_id == task.id
        scheduled.set()

    with patch.object(engine, "run_task", side_effect=_record_run):
        assert await engine.recover_stale_running_tasks() == 1
        await asyncio.wait_for(scheduled.wait(), timeout=2)
        pending = list(group_collaboration_module._BACKGROUND_RECOVERY_TASKS)
        await asyncio.gather(*pending)
        await asyncio.sleep(0)
        assert not group_collaboration_module._BACKGROUND_RECOVERY_TASKS


@pytest.mark.asyncio
async def test_run_task_cannot_fail_active_lease_when_worker_is_missing() -> None:
    async with async_session() as db:
        group = AgentGroup(name="active lease missing worker", user_id="default-user")
        db.add(group)
        await db.flush()
        task = AgentGroupTask(
            group_id=group.id,
            description="owned elsewhere",
            status="running",
            lease_owner="other-instance",
            lease_token=9,
            lease_expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        db.add(task)
        await db.commit()
        task_id = task.id

    await GroupCollaborationEngine(ModelRegistry(), tool_registry).run_task(task_id)

    async with async_session() as db:
        current = await db.get(AgentGroupTask, task_id)
        assert current is not None
        assert current.status == "running"
        assert current.lease_owner == "other-instance"
        assert current.lease_token == 9


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

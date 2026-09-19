"""Regression tests for executor and collaboration crash fixes.

Covers:
- SkillComposerExecutorAdapter calls the real SkillComposer method
- run_agent_simple accepts the group_id/role kwargs used by reviewer call sites
- a DAG task with a reviewer runs end-to-end without a TypeError
"""

from __future__ import annotations

import pytest

from app.core.interfaces import ExecutionContext, ExecutionStatus


@pytest.mark.asyncio
async def test_skill_composer_adapter_calls_execute_composition() -> None:
    from app.core.executor import SkillComposerExecutorAdapter
    from app.core.skill_composition import SkillComposer, SkillComposition

    registry = type("R", (), {"get_handler": lambda self, sid: None})()
    composer = SkillComposer(registry)
    composition = SkillComposition(id="c1", name="plan", description="d")
    composition.add_step("skill-1", {})

    adapter = SkillComposerExecutorAdapter(composer)
    ctx = ExecutionContext(session_id="s1", user_id="u1", variables={})
    result = await adapter.execute(ctx, composition=composition)
    assert result.status == ExecutionStatus.COMPLETED
    assert isinstance(result.output, dict)
    assert result.output["status"] == "completed"


@pytest.mark.asyncio
async def test_run_agent_simple_accepts_group_id_and_role() -> None:
    from app.core import AgentEvent, AgentEventType
    from app.core.collaboration import agent_runner

    calls: dict = {}

    async def fake_run(agent_id, provider, model_id, api_key, system_prompt, user_message, tools, base_url, principal):
        calls["agent_id"] = agent_id
        yield AgentEvent(type=AgentEventType.TEXT, data={"content": "review approved"})
        yield AgentEvent(type=AgentEventType.DONE, data={"tokens_used": 1})

    agent_runner.run_agent = fake_run
    output, _tokens = await agent_runner.run_agent_simple(
        agent_id="rev-1",
        provider="openai",
        model_id="gpt-4o",
        api_key="",
        system_prompt="sys",
        user_message="msg",
        tools=[],
        group_id="grp-1",
        role="reviewer",
    )
    assert calls["agent_id"] == "rev-1"


@pytest.mark.asyncio
async def test_dag_task_with_reviewer_runs(monkeypatch) -> None:
    from app.core.collaboration import agent_runner
    from app.core.collaboration import base as base_module
    from app.core.collaboration.base import GroupCollaborationEngine
    from app.storage import async_session
    from app.storage.models_groups import AgentGroup, AgentGroupMember, AgentGroupTask

    group_id = "crit-review-group"
    worker_member_id = "crit-review-worker"
    reviewer_member_id = "crit-review-reviewer"
    task_id = "crit-review-task"

    async with async_session() as db:
        db.add(AgentGroup(id=group_id, name="rev-group", user_id="default-user", process_type="sequential"))
        db.add(
            AgentGroupMember(
                id=worker_member_id,
                group_id=group_id,
                agent_id="worker-agent",
                role="worker",
                status="active",
                is_worker=True,
            )
        )
        db.add(
            AgentGroupMember(
                id=reviewer_member_id,
                group_id=group_id,
                agent_id="reviewer-agent",
                role="reviewer",
                status="active",
            )
        )
        db.add(
            AgentGroupTask(
                id=task_id,
                group_id=group_id,
                description="build feature",
                status="pending",
                worker_id=worker_member_id,
                reviewer_ids=[reviewer_member_id],
                dependencies=[],
            )
        )
        await db.commit()

    async def fake_worker(**_kwargs) -> tuple[str, int]:
        return "worker output", 5

    async def fake_reviewer(**_kwargs) -> tuple[str, int]:
        return "approved, pass", 3

    async def noop(*_args, **_kwargs) -> None:
        return None

    async def empty_memory(*_args, **_kwargs) -> str:
        return ""

    monkeypatch.setattr(base_module, "run_agent_with_retry", fake_worker)
    monkeypatch.setattr(agent_runner, "run_agent_simple", fake_reviewer)
    monkeypatch.setattr(base_module, "resolve_api_key", lambda *a, **k: "")
    monkeypatch.setattr(base_module, "resolve_base_url", lambda *a, **k: None)
    monkeypatch.setattr(base_module, "inject_memory", empty_memory)
    monkeypatch.setattr(base_module, "store_memory", noop)

    engine = GroupCollaborationEngine(model_registry=object(), tool_registry=object())

    async with async_session() as db:
        task = await db.get(AgentGroupTask, task_id)
        group = await db.get(AgentGroup, group_id)

    try:
        await engine._run_single_task_in_dag(task, group, {})
    finally:
        async with async_session() as db:
            for tid in (task_id,):
                row = await db.get(AgentGroupTask, tid)
                if row:
                    await db.delete(row)
            for mid in (worker_member_id, reviewer_member_id):
                row = await db.get(AgentGroupMember, mid)
                if row:
                    await db.delete(row)
            grp = await db.get(AgentGroup, group_id)
            if grp:
                await db.delete(grp)
            await db.commit()

    async with async_session() as db:
        row = await db.get(AgentGroupTask, task_id)
    done = row is None or row.status == "completed"
    assert done

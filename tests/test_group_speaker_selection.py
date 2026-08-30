"""LLM speaker selection for group-chat collaboration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app.core.group_collaboration import GroupCollaborationEngine, TaskLease
from app.models.registry import ModelRegistry
from app.storage import async_session
from app.storage.models_groups import AgentGroup, AgentGroupMember, AgentGroupTask


def _members(group_id: str) -> list[AgentGroupMember]:
    return [
        AgentGroupMember(group_id=group_id, agent_id="planner", role="worker"),
        AgentGroupMember(group_id=group_id, agent_id="reviewer", role="reviewer"),
    ]


@pytest.mark.asyncio
async def test_manager_llm_selects_named_candidate():
    engine = GroupCollaborationEngine(ModelRegistry(), object())
    engine._run_agent_simple = AsyncMock(return_value=(' {"agent_id": "reviewer"} ', 4))
    group = AgentGroup(id="group-1", name="team", manager_llm="openai/gpt-4o-mini")
    candidates = _members(group.id)

    selected = await engine._select_group_chat_speaker(
        group,
        task_description="Review a design",
        candidates=candidates,
        conversation=[{"agent_id": "planner", "content": "Initial plan"}],
    )

    assert selected.agent_id == "reviewer"


@pytest.mark.asyncio
async def test_missing_manager_llm_uses_deterministic_fallback():
    engine = GroupCollaborationEngine(ModelRegistry(), object())
    engine._run_agent_simple = AsyncMock()
    group = AgentGroup(id="group-1", name="team")
    candidates = _members(group.id)

    selected = await engine._select_group_chat_speaker(
        group,
        task_description="Review a design",
        candidates=candidates,
        conversation=[],
    )

    assert selected is candidates[0]
    engine._run_agent_simple.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_or_failed_selection_uses_first_candidate():
    engine = GroupCollaborationEngine(ModelRegistry(), object())
    group = AgentGroup(id="group-1", name="team", manager_llm="openai/gpt-4o-mini")
    candidates = _members(group.id)
    engine._run_agent_simple = AsyncMock(return_value=("unknown-agent", 1))

    invalid = await engine._select_group_chat_speaker(
        group,
        task_description="Review a design",
        candidates=candidates,
        conversation=[],
    )
    engine._run_agent_simple = AsyncMock(side_effect=RuntimeError("provider unavailable"))
    failed = await engine._select_group_chat_speaker(
        group,
        task_description="Review a design",
        candidates=candidates,
        conversation=[],
    )

    assert invalid is candidates[0]
    assert failed is candidates[0]


@pytest.mark.asyncio
async def test_selector_rejects_empty_candidate_list():
    engine = GroupCollaborationEngine(ModelRegistry(), object())
    group = AgentGroup(id="group-1", name="team", manager_llm="openai/gpt-4o-mini")

    with pytest.raises(ValueError, match="No speaker candidates"):
        await engine._select_group_chat_speaker(
            group,
            task_description="Review a design",
            candidates=[],
            conversation=[],
        )


@pytest.mark.asyncio
async def test_group_chat_process_uses_selected_speaker_order():
    async with async_session() as db:
        group = AgentGroup(
            name="speaker-order",
            user_id="default-user",
            process_type="group_chat",
            manager_llm="openai/gpt-4o-mini",
        )
        group.members = _members(group.id)
        db.add(group)
        await db.flush()
        task = AgentGroupTask(
            group_id=group.id,
            description="Review a design",
            status="running",
            max_rounds=1,
            lease_token=1,
        )
        db.add(task)
        await db.commit()

    engine = GroupCollaborationEngine(ModelRegistry(), object())
    planner, reviewer = group.members
    engine._select_group_chat_speaker = AsyncMock(side_effect=[reviewer, planner])
    engine._run_agent_simple = AsyncMock(side_effect=[("review", 1), ("plan", 1)])
    engine._task_is_running = AsyncMock(return_value=True)
    engine._complete_running_task = AsyncMock(return_value=True)
    engine._store_memory = AsyncMock()
    engine._invoke_step_callback = AsyncMock()
    engine._invoke_task_callback = AsyncMock()
    lease = TaskLease(
        task_id=task.id,
        owner=engine.instance_id,
        token=1,
        expires_at=datetime.now(UTC) + timedelta(minutes=1),
    )

    from app.core import group_collaboration as module

    original_broadcast = module.group_ws_hub.broadcast
    module.group_ws_hub.broadcast = AsyncMock()
    try:
        await engine._run_group_chat_process(task, group, lease)
    finally:
        broadcast = module.group_ws_hub.broadcast
        module.group_ws_hub.broadcast = original_broadcast

    turns = [
        call.args[1]["data"]["member_name"]
        for call in broadcast.await_args_list
        if call.args[1]["type"] == "group_chat_turn"
    ]
    assert turns == ["reviewer", "planner"]

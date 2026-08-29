"""Focused regression tests for bounded API list queries."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.api.v1._shared import _agents_cache, _hybrid_agents
from app.api.v1.tasks_api import _tasks_cache
from app.storage import async_session, engine
from app.storage.database import Agent
from app.storage.models_groups import AgentGroup, AgentGroupMember, AgentGroupTask


@pytest_asyncio.fixture
async def paginated_resources():
    async with engine.begin() as connection:
        await connection.run_sync(
            lambda sync_connection: AgentGroupTask.__table__.create(
                sync_connection, checkfirst=True
            )
        )

    base_time = datetime(2026, 1, 1)
    agents = [
        Agent(
            user_id="default-user",
            name=f"agent-{index:03d}",
            provider="test",
            model_id="test-model",
            created_at=base_time + timedelta(seconds=index),
        )
        for index in range(105)
    ]
    groups = [
        AgentGroup(
            name=f"group-{index:03d}",
            created_at=base_time + timedelta(seconds=index),
        )
        for index in range(105)
    ]

    async with async_session() as db:
        db.add_all([*agents, *groups])
        await db.flush()
        db.add(AgentGroupMember(group_id=groups[-1].id, agent_id=agents[-1].id))
        db.add_all(
            AgentGroupTask(
                group_id=groups[index].id,
                description=f"task-{index:03d}",
                status="running" if index % 2 else "pending",
                created_at=base_time + timedelta(seconds=index),
            )
            for index in range(105)
        )
        await db.commit()

    _agents_cache.set(None)
    await _hybrid_agents.invalidate_scalar()
    _tasks_cache.invalidate_all()


@pytest.mark.asyncio
async def test_agents_groups_and_tasks_are_paginated(client, paginated_resources):
    endpoints = [
        ("/api/v1/agents", "name"),
        ("/api/v1/groups", "name"),
        ("/api/v1/tasks", "description"),
    ]

    for path, label_key in endpoints:
        default_response = await client.get(path)
        page_response = await client.get(path, params={"limit": 5, "offset": 10})
        invalid_response = await client.get(path, params={"limit": 501})

        assert default_response.status_code == 200
        assert len(default_response.json()) == 100
        assert default_response.json()[0][label_key].endswith("104")
        assert page_response.status_code == 200
        assert len(page_response.json()) == 5
        assert page_response.json()[0][label_key].endswith("094")
        assert page_response.json()[-1][label_key].endswith("090")
        assert invalid_response.status_code == 422

    assert len((await client.get("/api/v1/groups")).json()[0]["members"]) == 1


@pytest.mark.asyncio
async def test_tasks_can_be_filtered_by_status(client, paginated_resources):
    response = await client.get("/api/v1/tasks", params={"status": "pending"})

    assert response.status_code == 200
    assert response.json()
    assert all(task["status"] == "pending" for task in response.json())


@pytest.mark.asyncio
async def test_task_status_change_invalidates_cached_list(client):
    async with async_session() as db:
        group = AgentGroup(name="cache-invalidation-group")
        db.add(group)
        await db.flush()
        task = AgentGroupTask(
            group_id=group.id,
            description="cached-running-task",
            status="running",
            lease_owner="worker-1",
            lease_token=4,
            lease_expires_at=datetime.now(UTC) + timedelta(minutes=1),
        )
        db.add(task)
        await db.commit()
        task_id = task.id

    _tasks_cache.invalidate_all()
    initial_response = await client.get("/api/v1/tasks")
    with patch(
        "app.core.group_collaboration.group_collaboration_engine.cancel_and_wait",
        new_callable=AsyncMock,
        return_value=True,
    ) as cancel_running_task:
        pause_response = await client.post(f"/api/v1/tasks/{task_id}/pause")
    updated_response = await client.get("/api/v1/tasks")

    assert initial_response.status_code == 200
    assert initial_response.json()[0]["status"] == "running"
    assert pause_response.status_code == 200
    cancel_running_task.assert_awaited_once_with(task_id)
    assert updated_response.json()[0]["status"] == "paused"
    async with async_session() as db:
        paused = await db.get(AgentGroupTask, task_id)
        assert paused is not None
        assert paused.lease_owner is None
        assert paused.lease_expires_at is None
        assert paused.lease_token == 5


@pytest.mark.asyncio
async def test_stop_task_waits_for_local_executor(client):
    async with async_session() as db:
        group = AgentGroup(name="stop-running-group")
        db.add(group)
        await db.flush()
        task = AgentGroupTask(group_id=group.id, description="stop me", status="running")
        db.add(task)
        await db.commit()
        task_id = task.id

    with patch(
        "app.core.group_collaboration.group_collaboration_engine.cancel_and_wait",
        new_callable=AsyncMock,
        return_value=True,
    ) as cancel_running_task:
        response = await client.post(f"/api/v1/tasks/{task_id}/stop")

    assert response.status_code == 200
    cancel_running_task.assert_awaited_once_with(task_id)
    async with async_session() as db:
        stopped = await db.get(AgentGroupTask, task_id)
        assert stopped is not None
        assert stopped.status == "stopped"


@pytest.mark.asyncio
async def test_task_list_reflects_background_status_changes(client):
    async with async_session() as db:
        group = AgentGroup(name="background-status-group")
        db.add(group)
        await db.flush()
        task = AgentGroupTask(
            group_id=group.id,
            description="background-status-task",
            status="running",
        )
        db.add(task)
        await db.commit()
        task_id = task.id

    _tasks_cache.invalidate_all()
    initial_response = await client.get("/api/v1/tasks")
    assert initial_response.json()[0]["status"] == "running"

    async with async_session() as db:
        task = await db.get(AgentGroupTask, task_id)
        assert task is not None
        task.status = "completed"
        await db.commit()

    updated_response = await client.get("/api/v1/tasks")
    assert updated_response.json()[0]["status"] == "completed"


@pytest.mark.asyncio
async def test_cancel_task_interrupts_running_engine_and_preserves_cancelled_status(client):
    async with async_session() as db:
        group = AgentGroup(name="cancel-running-group")
        db.add(group)
        await db.flush()
        task = AgentGroupTask(
            group_id=group.id,
            description="cancel-running-task",
            status="running",
            lease_owner="worker-1",
            lease_token=7,
            lease_expires_at=datetime.now(UTC) + timedelta(minutes=1),
        )
        db.add(task)
        await db.commit()
        task_id = task.id

    with patch(
        "app.core.group_collaboration.group_collaboration_engine.cancel_and_wait",
        new_callable=AsyncMock,
        return_value=True,
    ) as cancel_running_task:
        response = await client.post(f"/api/v1/tasks/{task_id}/cancel")

    assert response.status_code == 200
    cancel_running_task.assert_called_once_with(task_id)
    async with async_session() as db:
        task = await db.get(AgentGroupTask, task_id)
        assert task is not None
        assert task.status == "cancelled"
        assert task.completed_at is not None
        assert task.lease_owner is None
        assert task.lease_expires_at is None
        assert task.lease_token == 8


@pytest.mark.asyncio
async def test_resume_task_schedules_checkpoint_execution(client):
    async with async_session() as db:
        group = AgentGroup(name="resume-paused-group")
        db.add(group)
        await db.flush()
        task = AgentGroupTask(
            group_id=group.id,
            description="resume-paused-task",
            status="paused",
            lease_owner="stale-worker",
            lease_token=2,
            lease_expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        db.add(task)
        await db.commit()
        task_id = task.id

    def _close_spawned(coro):
        coro.close()

    with (
        patch(
            "app.core.group_collaboration.group_collaboration_engine.run_task",
            new_callable=AsyncMock,
        ) as run_task,
        patch("app.api.v1.tasks_api._spawn", side_effect=_close_spawned) as spawn,
    ):
        response = await client.post(f"/api/v1/tasks/{task_id}/resume")

    assert response.status_code == 200
    assert response.json()["status"] == "running"
    run_task.assert_called_once_with(task_id)
    spawn.assert_called_once()
    async with async_session() as db:
        task = await db.get(AgentGroupTask, task_id)
        assert task is not None
        assert task.status == "pending"
        assert task.paused_at is None
        assert task.lease_owner is None
        assert task.lease_expires_at is None
        assert task.lease_token == 3

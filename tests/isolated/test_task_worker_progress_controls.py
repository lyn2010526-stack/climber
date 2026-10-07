"""Offline task-control regressions using a private temporary database.

Run with --noconftest and dotenv loading disabled before importing the app.
Handlers are scripted; no model, tools, or business database are exercised.
"""

import asyncio
import json
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.routes import tasks as task_routes
from app.core import task_worker
from app.storage.models_platform import AutoLoopTask


@pytest_asyncio.fixture
async def manager(monkeypatch, tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'tasks.sqlite'}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(AutoLoopTask.__table__.create)
    monkeypatch.setattr(task_worker, "async_session", sessions)
    worker = task_worker.TaskManager(max_workers=1, max_task_retries=2)
    try:
        yield worker
    finally:
        tasks = list(worker._active_tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await engine.dispose()


@pytest.mark.asyncio
async def test_retry_persists_progress_and_checkpoint(manager):
    attempts = 0

    async def handler(payload, on_progress):
        nonlocal attempts
        attempts += 1
        await on_progress(attempts, 2, f"attempt {attempts}")
        if attempts == 1:
            raise RuntimeError("scripted transient failure")
        return {"output": "ok"}

    manager.register("scripted", handler)
    task_id = await manager.submit("scripted", {})
    await asyncio.wait_for(manager._active_tasks[task_id], 3)
    state = await manager.get_status(task_id)
    assert state["status"] == "completed"
    assert state["retry_count"] == 1
    assert state["checkpoint"]["step"] == 2
    assert state["progress_evaluation"]["percent"] == 100
    assert state["progress_evaluation"]["message"] == "attempt 2"
    assert any(event["data"].get("step") == 2 for event in manager._event_history[task_id])


@pytest.mark.asyncio
async def test_subtask_completion_aggregates_parent_progress_and_status(manager):
    async def handler(payload, on_progress):
        return {"output": "awaiting subtasks"}

    manager.register("scripted", handler)
    task_id = await manager.submit(
        "scripted",
        {
            "subtasks": [
                {"id": "first", "description": "First"},
                {"id": "second", "description": "Second", "dependencies": ["first"]},
            ]
        },
    )
    claimed = await manager.claim_subtasks(task_id, owner_id="default-user", agent_id="agent")
    assert [item["id"] for item in claimed] == ["first"]
    completed = await manager.complete_subtask(
        task_id, "first", owner_id="default-user", agent_id="agent", result={"ok": True}
    )
    assert completed["status"] == "completed"
    state = await manager.get_status(task_id)
    assert state["status"] == "running"
    assert state["progress"] == 1
    assert state["total_steps"] == 2
    claimed = await manager.claim_subtasks(task_id, owner_id="default-user", agent_id="agent")
    assert [item["id"] for item in claimed] == ["second"]
    await manager.complete_subtask(
        task_id, "second", owner_id="default-user", agent_id="agent", result={"ok": True}
    )
    state = await manager.get_status(task_id)
    assert state["status"] == "completed"
    assert state["progress"] == 2


@pytest.mark.asyncio
async def test_expired_subtask_lease_is_reclaimable(manager):
    async def handler(payload, on_progress):
        return {"output": "awaiting subtasks"}

    manager.register("scripted", handler)
    task_id = await manager.submit("scripted", {"subtasks": [{"description": "Work"}]})
    claimed = await manager.claim_subtasks(
        task_id, owner_id="default-user", agent_id="old", lease_seconds=1
    )
    assert claimed
    async with task_worker.async_session() as session:
        record = await session.get(AutoLoopTask, task_id)
        envelope = json.loads(record.objective)
        envelope["subtasks"][0]["lease_expires_at"] = (
            datetime.now(UTC) - timedelta(seconds=1)
        ).timestamp()
        record.objective = json.dumps(envelope)
        await session.commit()
    reclaimed = await manager.claim_subtasks(task_id, owner_id="default-user", agent_id="new")
    assert reclaimed[0]["claimed_by"] == "new"


@pytest.mark.asyncio
async def test_failed_subtask_fails_parent(manager):
    async def handler(payload, on_progress):
        return {"output": "awaiting subtasks"}

    manager.register("scripted", handler)
    task_id = await manager.submit("scripted", {"subtasks": [{"description": "Work"}]})
    await manager.claim_subtasks(task_id, owner_id="default-user", agent_id="agent")
    await manager.complete_subtask(
        task_id,
        "st-1",
        owner_id="default-user",
        agent_id="agent",
        error="failed work",
    )
    state = await manager.get_status(task_id)
    assert state["status"] == "failed"
    assert state["error"] == "A subtask failed"


@pytest.mark.asyncio
async def test_claim_issues_fencing_token_and_heartbeat(manager):
    manager.register("scripted", lambda payload, on_progress: asyncio.sleep(0))
    task_id = await manager.submit("scripted", {"subtasks": [{"description": "Work"}]})
    claimed = await manager.claim_subtasks(
        task_id, owner_id="default-user", agent_id="agent", worker_id="worker-1"
    )
    item = claimed[0]
    assert item["claim_token"]
    assert item["lease_version"] == 1
    assert item["worker_id"] == "worker-1"
    renewed = await manager.heartbeat_subtask(
        task_id,
        item["id"],
        owner_id="default-user",
        agent_id="agent",
        claim_token=item["claim_token"],
        lease_version=item["lease_version"],
    )
    assert renewed["status"] == "running"
    assert renewed["lease_expires_at"] > item["lease_expires_at"]


@pytest.mark.asyncio
async def test_stale_claim_cannot_complete_after_reclaim(manager):
    manager.register("scripted", lambda payload, on_progress: asyncio.sleep(0))
    task_id = await manager.submit("scripted", {"subtasks": [{"description": "Work"}]})
    old = (
        await manager.claim_subtasks(
            task_id, owner_id="default-user", agent_id="old", lease_seconds=1
        )
    )[0]
    async with task_worker.async_session() as session:
        record = await session.get(AutoLoopTask, task_id)
        envelope = json.loads(record.objective)
        envelope["subtasks"][0]["lease_expires_at"] = datetime.now(UTC).timestamp() - 1
        record.objective = json.dumps(envelope)
        await session.commit()
    new = (
        await manager.claim_subtasks(task_id, owner_id="default-user", agent_id="new")
    )[0]
    assert new["lease_version"] == old["lease_version"] + 1
    stale = await manager.complete_subtask(
        task_id,
        old["id"],
        owner_id="default-user",
        agent_id="old",
        claim_token=old["claim_token"],
        lease_version=old["lease_version"],
        result={"stale": True},
    )
    assert stale is None


@pytest.mark.asyncio
async def test_submit_rejects_cyclic_subtasks(manager):
    manager.register("scripted", lambda payload, on_progress: asyncio.sleep(0))
    with pytest.raises(ValueError, match="cycles"):
        await manager.submit(
            "scripted",
            {
                "subtasks": [
                    {"id": "a", "description": "A", "dependencies": ["b"]},
                    {"id": "b", "description": "B", "dependencies": ["a"]},
                ]
            },
        )


@pytest.mark.asyncio
async def test_running_subtask_completes_and_duplicate_completion_is_idempotent(manager):
    manager.register("scripted", lambda payload, on_progress: asyncio.sleep(0))
    task_id = await manager.submit("scripted", {"subtasks": [{"description": "Work"}]})
    item = (
        await manager.claim_subtasks(task_id, owner_id="default-user", agent_id="agent")
    )[0]
    await manager.heartbeat_subtask(
        task_id,
        item["id"],
        owner_id="default-user",
        agent_id="agent",
        claim_token=item["claim_token"],
        lease_version=item["lease_version"],
    )
    completed = await manager.complete_subtask(
        task_id,
        item["id"],
        owner_id="default-user",
        agent_id="agent",
        claim_token=item["claim_token"],
        lease_version=item["lease_version"],
        completion_id="completion-1",
        result={"ok": True},
    )
    duplicate = await manager.complete_subtask(
        task_id,
        item["id"],
        owner_id="default-user",
        agent_id="agent",
        claim_token=item["claim_token"],
        lease_version=item["lease_version"],
        completion_id="completion-1",
        result={"ok": True},
    )
    assert completed["status"] == "completed"
    assert duplicate == completed


@pytest.mark.asyncio
async def test_task_control_maps_value_error_to_conflict(monkeypatch):
    async def get_status(*args, **kwargs):
        return {"task_id": "task-1", "status": "running"}

    async def rollback(*args, **kwargs):
        raise ValueError("Rollback requires a stopped worker")

    monkeypatch.setattr(task_routes.task_manager, "get_status", get_status)
    monkeypatch.setattr(task_routes.task_manager, "rollback", rollback)

    with pytest.raises(HTTPException) as raised:
        await task_routes._control("task-1", "rollback", {"id": "owner"})

    assert raised.value.status_code == 409
    assert raised.value.detail == "Rollback requires a stopped worker"


@pytest.mark.asyncio
@pytest.mark.parametrize("control", ["cancel", "pause"])
@pytest.mark.parametrize("retrying", [False, True])
async def test_control_survives_handler_suppressing_cancellation(manager, control, retrying):
    started = asyncio.Event()
    attempts = 0

    async def handler(payload, on_progress):
        nonlocal attempts
        attempts += 1
        if retrying and attempts == 1:
            raise RuntimeError("scripted transient failure")
        await on_progress(1, 2, "before control")
        started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            return {"output": "late result"}

    manager.register("scripted", handler)
    task_id = await manager.submit("scripted", {})
    worker = manager._active_tasks[task_id]
    await asyncio.wait_for(started.wait(), 3)
    assert await getattr(manager, control)(task_id)
    await asyncio.wait_for(worker, 3)
    state = await manager.get_status(task_id)
    assert state["status"] == ("cancelled" if control == "cancel" else "paused")
    assert state["result"] is None
    assert state["checkpoint"]["step"] == 1
    assert all(
        event["data"].get("status") != "completed" for event in manager._event_history[task_id]
    )


@pytest.mark.asyncio
async def test_retry_budget_is_bounded_and_last_progress_is_durable(manager):
    attempts = 0

    async def handler(payload, on_progress):
        nonlocal attempts
        attempts += 1
        await on_progress(attempts, 4, "scripted failure")
        raise RuntimeError("scripted failure")

    manager.register("scripted", handler)
    task_id = await manager.submit("scripted", {})
    await asyncio.wait_for(manager._active_tasks[task_id], 3)
    state = await manager.get_status(task_id)
    assert attempts == 3
    assert state["status"] == "failed"
    assert state["retry_count"] == 2
    assert state["checkpoint"]["step"] == 3


@pytest.mark.asyncio
async def test_cancel_blocks_late_progress_after_cancellation_is_suppressed(manager):
    started = asyncio.Event()
    continued = []

    async def handler(payload, on_progress):
        await on_progress(1, 2, "before cancel")
        started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            await on_progress(2, 2, "late progress")
            continued.append(True)

    manager.register("scripted", handler)
    task_id = await manager.submit("scripted", {})
    worker = manager._active_tasks[task_id]
    await asyncio.wait_for(started.wait(), 3)
    assert await manager.cancel(task_id)
    await asyncio.wait_for(worker, 3)
    state = await manager.get_status(task_id)
    assert state["status"] == "cancelled"
    assert state["checkpoint"]["step"] == 1
    assert continued == []


@pytest.mark.asyncio
async def test_agent_retry_preserves_task_id_after_credential_resolution(manager, monkeypatch):
    retry_entered = asyncio.Event()
    release_retry = asyncio.Event()
    calls = []

    async def resolve(owner_id, payload):
        # Stored owner configuration deliberately contains no runtime fields.
        return {"goal": payload["goal"], "user_id": "ignored-owner"}

    async def handler(payload, on_progress):
        calls.append((payload["_task_id"], payload["user_id"]))
        if len(calls) == 1:
            raise RuntimeError("scripted transient failure")
        retry_entered.set()
        await release_retry.wait()
        await on_progress(2, 2, "retry completed")
        return {"output": "ok"}

    monkeypatch.setattr(task_worker, "resolve_owner_agent_payload", resolve)
    manager.register("agent_run", handler)
    async with task_worker.async_session() as db:
        db.add(
            AutoLoopTask(
                id="factory-retry",
                owner_id="alice",
                status="paused",
                objective=json.dumps({"type": "agent_run", "goal": "build"}),
            )
        )
        await db.commit()
    assert await manager.resume("factory-retry")
    worker = manager._active_tasks["factory-retry"]
    try:
        await asyncio.wait_for(retry_entered.wait(), 3)
    finally:
        release_retry.set()
        await asyncio.wait_for(worker, 3)
    assert calls == [("factory-retry", "alice"), ("factory-retry", "alice")]
    assert (await manager.get_status("factory-retry"))["status"] == "completed"


@pytest.mark.asyncio
@pytest.mark.parametrize("new_running", [False, True])
@pytest.mark.parametrize("old_exit", ["cancel", "return", "progress", "error"])
async def test_old_worker_cannot_own_resumed_run(manager, new_running, old_exit):
    if new_running:
        manager._semaphore = asyncio.Semaphore(2)
    old_started = asyncio.Event()
    old_cancelled = asyncio.Event()
    release_old = asyncio.Event()
    new_started = asyncio.Event()
    release_new = asyncio.Event()
    old_done = asyncio.Event()
    calls = 0

    async def handler(payload, on_progress):
        nonlocal calls
        calls += 1
        if calls == 1:
            await on_progress(1, 3, "old checkpoint")
            old_started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                old_cancelled.set()
                await release_old.wait()
                if old_exit == "cancel":
                    raise
                if old_exit == "error":
                    raise RuntimeError("stale worker failure") from None
                if old_exit == "progress":
                    await on_progress(99, 100, "stale progress")
                return {"output": "stale result"}
        await on_progress(2, 3, "new checkpoint")
        new_started.set()
        await release_new.wait()
        return {"output": "new result"}

    manager.register("scripted", handler)
    task_id = await manager.submit("scripted", {})
    old_worker = manager._active_tasks[task_id]
    old_worker.add_done_callback(lambda _done: old_done.set())
    await asyncio.wait_for(old_started.wait(), 3)
    assert await manager.pause(task_id)
    await asyncio.wait_for(old_cancelled.wait(), 3)
    assert await manager.resume(task_id)
    new_worker = manager._active_tasks[task_id]
    try:
        if new_running:
            await asyncio.wait_for(new_started.wait(), 3)
        else:
            assert (await manager.get_status(task_id))["status"] == "pending"
        marker = manager._event_sequence
        release_old.set()
        await asyncio.wait_for(old_worker, 3)
        await asyncio.wait_for(old_done.wait(), 3)
        assert manager._active_tasks[task_id] is new_worker
        state = await manager.get_status(task_id)
        assert state["status"] in {"pending", "running"}
        assert state["result"] is None
        assert state["retry_count"] == 0
        assert state["checkpoint"]["step"] in {1, 2}
        late_events = [
            event["data"] for event in manager._event_history[task_id] if event["sequence"] > marker
        ]
        assert all(
            event.get("status") not in {"cancelled", "failed", "completed"}
            and event.get("step") != 99
            for event in late_events
        )
    finally:
        release_old.set()
        release_new.set()
        await asyncio.wait_for(asyncio.gather(old_worker, new_worker), 3)
    state = await manager.get_status(task_id)
    assert state["status"] == "completed"
    assert state["result"] == {"output": "new result"}
    assert calls == 2


@pytest.fixture
def factory(manager, monkeypatch):
    monkeypatch.setattr(task_worker, "task_manager", manager)
    manager.register("factory_run", task_worker.handle_factory_run)

    async def resolve(owner_id, payload):
        return {**payload, "api_key": "synthetic-factory-secret", "user_id": owner_id}

    monkeypatch.setattr(task_worker, "resolve_owner_agent_payload", resolve)
    return manager


@pytest.mark.asyncio
@pytest.mark.parametrize("restart", [False, True])
async def test_factory_resume_skips_completed_write_and_continues(factory, monkeypatch, restart):
    paused_step = asyncio.Event()
    release = asyncio.Event()
    calls = []
    plan = {
        "steps": [
            {"action": "write", "objective": "write once", "tools": ["write_file"]},
            {"action": "inspect", "objective": "read remaining", "tools": ["read_file"]},
            {"action": "finish", "objective": "finish remaining", "tools": ["read_file"]},
        ]
    }

    async def agent(payload, on_progress):
        objective = payload["objective"]
        if objective.startswith("Create a concise"):
            calls.append("plan")
            return {"output": json.dumps(plan)}
        if objective.startswith("Produce the final"):
            assert "evidence" in objective
            return {"output": "report"}
        calls.append(objective)
        if objective == "read remaining" and calls.count(objective) == 1:
            paused_step.set()
            await release.wait()
        return {"output": "evidence"}

    factory.register("agent_run", agent)
    task_id = await factory.submit(
        "factory_run",
        {
            "objective": "implement bounded change",
            "factory_skills": ["file_manager"],
            "tools": ["write_file", "read_file"],
            "permission_mode": "auto",
            "api_key": "synthetic-factory-secret",
        },
    )
    old_worker = factory._active_tasks[task_id]
    await asyncio.wait_for(paused_step.wait(), 5)
    assert await factory.pause(task_id)
    await asyncio.wait_for(old_worker, 5)
    state = await factory.get_status(task_id)
    saved = state["checkpoint"]["factory"]
    assert saved["results"][0]["step"] == 1
    assert saved["in_flight"] == 2
    assert "synthetic-factory-secret" not in json.dumps(state["checkpoint"])
    if restart:
        factory = task_worker.TaskManager(max_workers=1)
        factory.register("factory_run", task_worker.handle_factory_run)
        factory.register("agent_run", agent)
        monkeypatch.setattr(task_worker, "task_manager", factory)
    release.set()
    assert await factory.resume(task_id)
    await asyncio.wait_for(factory._active_tasks[task_id], 5)
    state = await factory.get_status(task_id)
    assert state["status"] == "completed"
    assert calls.count("plan") == 1
    assert calls.count("write once") == 1
    assert calls.count("read remaining") == 2
    assert calls.count("finish remaining") == 1
    assert len(state["checkpoint"]["factory"]["results"]) == 3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "damage",
    [
        "none",
        "version",
        "owner",
        "fingerprint",
        "plan",
        "plan_digest",
        "results",
        "in_flight",
        "uncertain_write",
    ],
)
async def test_factory_invalid_or_uncertain_checkpoint_fails_closed(factory, damage):
    entered = asyncio.Event()
    calls = []

    async def agent(payload, on_progress):
        calls.append(payload["objective"])
        if payload["objective"].startswith("Create a concise"):
            return {
                "output": json.dumps(
                    {
                        "steps": [
                            {"action": "write", "objective": "write once", "tools": ["write_file"]},
                        ]
                    }
                )
            }
        entered.set()
        await asyncio.Event().wait()
        return {"output": "unreachable"}

    factory.register("agent_run", agent)
    task_id = await factory.submit(
        "factory_run",
        {
            "objective": "implement bounded change",
            "factory_skills": ["file_manager"],
            "tools": ["write_file"],
            "permission_mode": "auto",
        },
    )
    old_worker = factory._active_tasks[task_id]
    await asyncio.wait_for(entered.wait(), 5)
    assert await factory.pause(task_id)
    await asyncio.wait_for(old_worker, 5)
    async with task_worker.async_session() as db:
        row = await db.get(AutoLoopTask, task_id)
        cp = json.loads(json.dumps(row.checkpoint))
        if damage == "none":
            cp = None
        elif damage != "uncertain_write":
            cp["factory"][damage if damage != "owner" else "owner_id"] = {
                "version": 99,
                "owner": "other",
                "fingerprint": "mismatch",
                "plan": [],
                "plan_digest": "mismatch",
                "results": [{"step": 9}],
                "in_flight": "one",
            }[damage]
        row.checkpoint = cp
        await db.commit()
    before = list(calls)
    assert await factory.resume(task_id)
    await asyncio.wait_for(factory._active_tasks[task_id], 5)
    state = await factory.get_status(task_id)
    assert state["status"] == "failed"
    assert "manual review" in state["error"]
    assert state["retry_count"] == 0
    assert calls == before


@pytest.mark.asyncio
async def test_factory_failed_write_is_never_retried_as_whole_task(factory):
    calls = []

    async def agent(payload, on_progress):
        if payload["objective"].startswith("Create a concise"):
            return {
                "output": json.dumps(
                    {
                        "steps": [
                            {"action": "write", "objective": "write once", "tools": ["write_file"]},
                        ]
                    }
                )
            }
        calls.append(payload["objective"])
        raise RuntimeError("write outcome uncertain")

    factory.register("agent_run", agent)
    task_id = await factory.submit(
        "factory_run",
        {
            "objective": "implement bounded change",
            "factory_skills": ["file_manager"],
            "tools": ["write_file"],
            "permission_mode": "auto",
        },
    )
    await asyncio.wait_for(factory._active_tasks[task_id], 5)
    assert calls == ["write once"]
    state = await factory.get_status(task_id)
    assert state["status"] == "failed"
    assert state["retry_count"] == 0
    assert state["checkpoint"]["factory"]["in_flight"] == 1
    assert await factory.retry(task_id)
    await asyncio.wait_for(factory._active_tasks[task_id], 5)
    assert calls == ["write once"]
    assert (await factory.get_status(task_id))["status"] == "failed"


@pytest.mark.asyncio
async def test_factory_checkpoint_commit_failure_never_reexecutes_step(factory, monkeypatch):
    from sqlalchemy.ext.asyncio import AsyncSession

    executed = asyncio.Event()
    failed = False
    commits = []
    original_commit = AsyncSession.commit

    async def commit(db):
        nonlocal failed
        for row in db.dirty:
            if isinstance(row, AutoLoopTask) and row.checkpoint:
                snapshot = row.checkpoint.get("factory", {})
                if snapshot.get("results") and not failed:
                    failed = True
                    commits.append(json.loads(json.dumps(snapshot)))
                    raise RuntimeError("injected checkpoint commit failure")
        await original_commit(db)

    monkeypatch.setattr(AsyncSession, "commit", commit)
    calls = []

    async def agent(payload, on_progress):
        if payload["objective"].startswith("Create a concise"):
            return {
                "output": json.dumps(
                    {
                        "steps": [
                            {"action": "read", "objective": "first", "tools": ["read_file"]},
                            {"action": "read", "objective": "second", "tools": ["read_file"]},
                        ]
                    }
                )
            }
        calls.append(payload["objective"])
        executed.set()
        return {"output": "evidence"}

    factory.register("agent_run", agent)
    task_id = await factory.submit(
        "factory_run",
        {
            "objective": "inspect project",
            "factory_skills": ["code_reviewer"],
            "tools": ["read_file"],
            "permission_mode": "auto",
        },
    )
    worker = factory._active_tasks[task_id]
    await asyncio.wait_for(executed.wait(), 5)
    await asyncio.wait_for(worker, 5)
    assert failed
    assert calls == ["first"]
    assert len(commits[0]["results"]) == 1
    state = await factory.get_status(task_id)
    assert state["status"] == "failed"
    assert state["checkpoint"]["factory"]["results"] == []
    assert state["checkpoint"]["factory"]["in_flight"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("location", ["plan", "result"])
async def test_redacted_factory_content_blocks_resume(factory, location):
    entered = asyncio.Event()
    calls = []
    synthetic_key = "synthetic-factory-secret"

    async def agent(payload, on_progress):
        objective = payload["objective"]
        if objective.startswith("Create a concise"):
            return {
                "output": json.dumps(
                    {
                        "steps": [
                            {
                                "action": "read",
                                "objective": synthetic_key if location == "plan" else "first",
                                "tools": ["read_file"],
                            },
                            {"action": "read", "objective": "second", "tools": ["read_file"]},
                        ]
                    }
                )
            }
        calls.append(objective)
        if objective == "second":
            entered.set()
            await asyncio.Event().wait()
        return {"output": synthetic_key if location == "result" else "evidence"}

    factory.register("agent_run", agent)
    task_id = await factory.submit(
        "factory_run",
        {
            "objective": "inspect project",
            "factory_skills": ["code_reviewer"],
            "tools": ["read_file"],
            "permission_mode": "auto",
            "api_key": synthetic_key,
        },
    )
    worker = factory._active_tasks[task_id]
    await asyncio.wait_for(entered.wait(), 5)
    assert await factory.pause(task_id)
    await asyncio.wait_for(worker, 5)
    state = await factory.get_status(task_id)
    assert synthetic_key not in json.dumps(state["checkpoint"])
    assert state["checkpoint"]["factory"]["recovery_blocked"]
    before = list(calls)
    assert await factory.resume(task_id)
    await asyncio.wait_for(factory._active_tasks[task_id], 5)
    assert calls == before
    assert (await factory.get_status(task_id))["status"] == "failed"


@pytest.mark.asyncio
async def test_rollback_refuses_live_worker_even_after_pause(manager):
    started = asyncio.Event()
    cancelled = asyncio.Event()
    release = asyncio.Event()
    calls = []

    async def handler(payload, on_progress):
        calls.append("action")
        await on_progress(1, 2, "checkpoint")
        started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.set()
            await release.wait()
            raise

    manager.register("scripted", handler)
    task_id = await manager.submit("scripted", {})
    worker = manager._active_tasks[task_id]
    await asyncio.wait_for(started.wait(), 5)
    try:
        with pytest.raises(ValueError, match="stopped worker"):
            await manager.rollback(task_id)
        assert await manager.pause(task_id)
        await asyncio.wait_for(cancelled.wait(), 5)
        with pytest.raises(ValueError, match="stopped worker"):
            await manager.rollback(task_id)
        assert manager._active_tasks[task_id] is worker
        assert calls == ["action"]
    finally:
        release.set()
        await asyncio.wait_for(worker, 5)


@pytest.mark.asyncio
async def test_requeued_restart_requires_explicit_resume_and_keeps_completed_write(
    factory, monkeypatch
):
    started = asyncio.Event()
    calls = []

    async def agent(payload, on_progress):
        objective = payload["objective"]
        if objective.startswith("Create a concise"):
            return {
                "output": json.dumps(
                    {
                        "steps": [
                            {"action": "write", "objective": "write once", "tools": ["write_file"]},
                            {"action": "read", "objective": "remaining", "tools": ["read_file"]},
                        ]
                    }
                )
            }
        if objective.startswith("Produce the final"):
            return {"output": "report"}
        calls.append(objective)
        if objective == "remaining" and calls.count(objective) == 1:
            started.set()
            await asyncio.Event().wait()
        return {"output": "evidence"}

    factory.register("agent_run", agent)
    task_id = await factory.submit(
        "factory_run",
        {
            "objective": "implement bounded change",
            "factory_skills": ["file_manager"],
            "tools": ["write_file", "read_file"],
            "permission_mode": "auto",
        },
    )
    worker = factory._active_tasks[task_id]
    await asyncio.wait_for(started.wait(), 5)
    assert await factory.pause(task_id)
    await asyncio.wait_for(worker, 5)
    async with task_worker.async_session() as db:
        row = await db.get(AutoLoopTask, task_id)
        row.error = "previous failure"
        row.result = {"output": "stale"}
        await db.commit()
    async with factory.slot():
        assert await factory.resume(task_id)
        queued = factory._active_tasks[task_id]
        state = await factory.get_status(task_id)
        assert state["error"] is None
        assert state["result"] is None
        assert state["progress"] == 1
        queued.cancel()
        await asyncio.gather(queued, return_exceptions=True)
    restarted = task_worker.TaskManager(max_workers=1)
    restarted.register("factory_run", task_worker.handle_factory_run)
    restarted.register("agent_run", agent)
    monkeypatch.setattr(task_worker, "task_manager", restarted)
    before = list(calls)
    assert await restarted.recover_pending_tasks() == 0
    state = await restarted.get_status(task_id)
    assert state["status"] == "paused"
    assert "explicit resume" in state["error"]
    assert calls == before
    assert await restarted.resume(task_id)
    await asyncio.wait_for(restarted._active_tasks[task_id], 5)
    state = await restarted.get_status(task_id)
    assert state["status"] == "completed"
    assert state["error"] is None
    assert calls.count("write once") == 1
    assert calls.count("remaining") == 2

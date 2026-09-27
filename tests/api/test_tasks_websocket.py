"""Regression tests for task authentication, ownership, and socket cleanup."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.storage import async_session
from app.storage.database import Session
from app.storage.models_platform import AutoLoopTask, Workflow
from tests.api.conftest import bearer


async def _seed_task(
    task_id: str,
    owner_id: str,
    *,
    session_id: str | None = None,
    workflow_id: str | None = None,
) -> None:
    objective = {"type": "agent_run", "_owner_id": owner_id}
    if session_id:
        objective["session_id"] = session_id
    if workflow_id:
        objective["workflow_id"] = workflow_id
    async with async_session() as db:
        db.add(
            AutoLoopTask(
                id=task_id,
                objective=json.dumps(objective),
                status="pending",
                max_steps=1,
                current_step=0,
            )
        )
        await db.commit()


async def _seed_session(session_id: str, owner_id: str) -> None:
    async with async_session() as db:
        db.add(Session(id=session_id, user_id=owner_id, title="private", status="idle"))
        await db.commit()


async def _seed_workflow(workflow_id: str, owner_id: str) -> None:
    async with async_session() as db:
        db.add(Workflow(id=workflow_id, user_id=owner_id, name="private"))
        await db.commit()


def _open_task_socket(client: TestClient, task_id: str | None, headers: dict[str, str]) -> None:
    query = f"?task_id={task_id}" if task_id else ""
    with client.websocket_connect(f"/api/v1/tasks/ws{query}", headers=headers):
        pass


async def test_task_submit_requires_authentication(http, auth_on) -> None:
    response = await http.post("/api/v1/tasks/submit", json={"task_type": "agent_run"})
    assert response.status_code == 401


@pytest.mark.parametrize("path", ["/api/v1/tasks/owned-task", "/api/v1/tasks/"])
async def test_task_reads_require_authentication(http, auth_on, path: str) -> None:
    response = await http.get(path)

    assert response.status_code == 401


async def test_task_status_and_list_are_scoped_to_the_owner(http, auth_on) -> None:
    await _seed_task("private-task", "owner-user")

    status = await http.get("/api/v1/tasks/private-task", headers=bearer("intruder-user"))
    listed = await http.get("/api/v1/tasks/", headers=bearer("intruder-user"))

    assert status.status_code == 404
    assert status.json()["detail"] == "Task not found"
    assert all(item["task_id"] != "private-task" for item in listed.json())


async def test_task_cancel_is_owner_scoped(http, auth_on) -> None:
    await _seed_task("private-cancel-task", "owner-user")

    response = await http.post(
        "/api/v1/tasks/private-cancel-task/cancel",
        headers=bearer("intruder-user", ["write"]),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


async def test_task_submit_rejects_foreign_session(http, auth_on) -> None:
    await _seed_session("private-session", "owner-user")
    response = await http.post(
        "/api/v1/tasks/submit",
        json={"task_type": "agent_run", "payload": {"session_id": "private-session"}},
        headers=bearer("intruder-user", ["write"]),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Session not found"


@pytest.mark.parametrize("resource", ["session", "workflow"])
async def test_task_websocket_rejects_foreign_resource(http, auth_on, resource: str) -> None:
    if resource == "session":
        await _seed_session("private-session", "owner-user")
        await _seed_task("foreign-session-task", "owner-user", session_id="private-session")
        task_id = "foreign-session-task"
    else:
        await _seed_workflow("private-workflow", "owner-user")
        await _seed_task("foreign-workflow-task", "owner-user", workflow_id="private-workflow")
        task_id = "foreign-workflow-task"

    with TestClient(app) as client, pytest.raises(WebSocketDisconnect):
        _open_task_socket(client, task_id, bearer("intruder-user"))


async def test_task_websocket_requires_task_id_and_cleans_up(auth_on, monkeypatch) -> None:
    from app.api.v1.routes import tasks

    await _seed_task("owned-task", "owner-user")
    monkeypatch.setattr(tasks.settings, "enable_auth", True)

    with TestClient(app) as client, pytest.raises(WebSocketDisconnect):
        _open_task_socket(client, None, bearer("owner-user"))
    with TestClient(app) as client:
        with client.websocket_connect(
            "/api/v1/tasks/ws?task_id=owned-task", headers=bearer("owner-user")
        ):
            assert tasks._ws_clients
        assert tasks._ws_clients == {}

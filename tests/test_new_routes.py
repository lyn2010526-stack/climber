"""Smoke tests for the routes that were previously missing."""

import os
from unittest.mock import AsyncMock, patch

import pytest

os.environ["APP_TESTING"] = "true"
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./data/e2e.db")

from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_groups_roundtrip(client):
    agent = client.post("/api/v1/agents", json={"name": "GroupAgent"}).json()
    created = client.post("/api/v1/groups", json={"name": "E2E Group"})
    assert created.status_code == 200, created.text
    gid = created.json()["id"]

    assert client.get(f"/api/v1/groups/{gid}").status_code == 200
    assert any(g["id"] == gid for g in client.get("/api/v1/groups").json())

    added = client.post(f"/api/v1/groups/{gid}/members", json={"agent_id": agent["id"], "role": "worker"})
    assert added.status_code == 200

    assert client.delete(f"/api/v1/groups/{gid}").status_code == 200
    assert client.get(f"/api/v1/groups/{gid}").status_code == 404


def test_tasks_roundtrip(client):
    agent = client.post("/api/v1/agents", json={"name": "TaskAgent"}).json()
    group = client.post("/api/v1/groups", json={"name": "TaskGroup"}).json()
    member = client.post(f"/api/v1/groups/{group['id']}/members", json={"agent_id": agent["id"], "role": "worker"}).json()
    created = client.post("/api/v1/tasks", json={"group_id": group["id"], "description": "do stuff", "worker_id": member["id"]})
    assert created.status_code == 200, created.text
    tid = created.json()["id"]

    def _close_spawned(coro):
        coro.close()

    with (
        patch(
            "app.core.group_collaboration.group_collaboration_engine.run_task",
            new_callable=AsyncMock,
        ) as run_task,
        patch("app.api.v1.tasks_api._spawn", side_effect=_close_spawned),
    ):
        assert client.post(f"/api/v1/tasks/{tid}/run").status_code == 200
    run_task.assert_called_once_with(tid)
    assert any(t["id"] == tid for t in client.get("/api/v1/tasks").json())
    assert client.get("/api/v1/tasks").status_code == 200


def test_run_missing_task_returns_not_found(client):
    response = client.post("/api/v1/tasks/missing-task/run")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_health_probes_use_http_status_for_orchestrators(client):
    class _ReadyChecker:
        async def readiness(self):
            return False

        async def liveness(self):
            return True

    with patch("app.core.health_check.get_health_checker", return_value=_ReadyChecker()):
        ready = client.get("/api/v1/health/ready")
        live = client.get("/api/v1/health/live")

    assert ready.status_code == 503
    assert ready.json() == {"ready": False}
    assert live.status_code == 200
    assert live.json() == {"alive": True}


def test_scheduler_roundtrip(client):
    created = client.post("/api/v1/scheduler", json={"name": "daily", "schedule": "0 9 * * *"})
    assert created.status_code == 200, created.text
    assert client.get("/api/v1/scheduler").status_code == 200


def test_mcp_roundtrip(client):
    created = client.post("/api/v1/mcp", json={"name": "local fs", "command": "python"})
    assert created.status_code == 200, created.text
    mid = created.json()["id"]

    assert client.get("/api/v1/mcp").status_code == 200
    assert client.post(f"/api/v1/mcp/{mid}/start").json()["status"] == "connected"
    assert client.post(f"/api/v1/mcp/{mid}/stop").json()["status"] == "stopped"
    assert client.delete(f"/api/v1/mcp/{mid}").status_code == 200


def test_eval_roundtrip(client):
    agent = client.post("/api/v1/agents", json={"name": "EvalAgent"}).json()
    ds = client.post("/api/v1/eval/datasets", json={"name": "unit", "data_json": "[]"})
    assert ds.status_code == 200, ds.text
    did = ds.json()["id"]

    run = client.post("/api/v1/eval/run", json={"dataset_id": did, "agent_id": agent["id"]})
    assert run.status_code == 200, run.text
    assert run.json()["verdict"] == "pass"
    assert client.get("/api/v1/eval/datasets").status_code == 200


def test_eval_run_gates_verdict(client):
    """Posted eval results with gates get a server-side CI verdict."""
    agent = client.post("/api/v1/agents", json={"name": "GateAgent"}).json()
    ds = client.post("/api/v1/eval/datasets", json={"name": "gated", "data_json": "[]"})
    did = ds.json()["id"]

    payload = {
        "dataset_id": did,
        "agent_id": agent["id"],
        "total_cases": 10,
        "passed_cases": 7,
        "failed_cases": 3,
        "pass_rate": 0.7,
        "average_score": 0.7,
        "gates": {"min_pass_rate": 0.9},
    }
    run = client.post("/api/v1/eval/run", json=payload)
    assert run.status_code == 200, run.text
    body = run.json()
    assert body["verdict"] == "fail"
    assert any("pass_rate" in f for f in body["gate_failures"])

    payload["gates"] = {"min_pass_rate": 0.5}
    ok = client.post("/api/v1/eval/run", json=payload)
    assert ok.json()["verdict"] == "pass"


def test_cost_roundtrip(client):
    assert client.get("/api/v1/cost/records").status_code == 200
    assert client.get("/api/v1/cost/budget").status_code == 200
    assert client.get("/api/v1/cost/quota").status_code == 200


def test_search_roundtrip(client):
    assert client.get("/api/v1/search").status_code == 200
    assert client.get("/api/v1/search?q=hello").status_code == 200


def test_ws_endpoint_exists():
    import app.api.v1.ws as g
    paths = [r.path for r in g.router.routes if type(r).__name__ == "APIWebSocketRoute"]
    assert any("/ws/" in p for p in paths), f"websocket route must be registered, got {paths}"

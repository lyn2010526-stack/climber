"""Smoke tests for the routes that were previously missing."""

import os

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

    assert client.post(f"/api/v1/tasks/{tid}/run").status_code == 200
    assert any(t["id"] == tid for t in client.get("/api/v1/tasks").json())
    assert client.get("/api/v1/tasks").status_code == 200


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
    assert client.get("/api/v1/eval/datasets").status_code == 200


def test_cost_roundtrip(client):
    assert client.get("/api/v1/cost/records").status_code == 200
    assert client.get("/api/v1/cost/budget").status_code == 200
    assert client.get("/api/v1/cost/quota").status_code == 200


def test_search_roundtrip(client):
    assert client.get("/api/v1/search").status_code == 200
    assert client.get("/api/v1/search?q=hello").status_code == 200


def test_ws_endpoint_exists():
    import app.api.v1.generic as g
    paths = [r.path for r in g.router.routes if type(r).__name__ == "APIWebSocketRoute"]
    assert any("/ws/" in p for p in paths), f"websocket route must be registered, got {paths}"

"""End-to-end smoke test hitting the exact paths the frontend calls."""

import os

os.environ["APP_TESTING"] = "true"
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./data/e2e.db")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_agent_crud_roundtrip(client):
    created = client.post("/api/v1/agents", json={"name": "E2E Agent", "provider": "openai", "model_id": "gpt-4o-mini"})
    assert created.status_code == 200, created.text
    agent_id = created.json()["id"]
    assert agent_id != "agent-1", "must not return a hardcoded id"

    listed = client.get("/api/v1/agents")
    assert listed.status_code == 200
    assert any(a["id"] == agent_id for a in listed.json()), "created agent must appear in list"

    deleted = client.delete(f"/api/v1/agents/{agent_id}")
    assert deleted.status_code == 200

    after = client.get("/api/v1/agents")
    assert not any(a["id"] == agent_id for a in after.json()), "deleted agent must disappear"

    assert client.delete(f"/api/v1/agents/{agent_id}").status_code == 404


def test_workflow_crud_and_persistence(client):
    payload = {
        "name": "E2E Workflow",
        "nodes": [{"id": "start", "type": "start", "data": {"label": "开始"}}],
        "edges": [],
    }
    created = client.post("/api/v1/workflows", json=payload)
    assert created.status_code == 200, created.text
    wf_id = created.json()["id"]
    assert wf_id != "workflow-1"

    assert any(w["id"] == wf_id for w in client.get("/api/v1/workflows").json())
    assert any(w["id"] == wf_id for w in client.get("/api/v1/workflows/").json())

    detail = client.get(f"/api/v1/workflows/{wf_id}")
    assert detail.status_code == 200
    assert detail.json()["nodes"][0]["id"] == "start"

    updated = client.put(f"/api/v1/workflows/{wf_id}", json={"name": "Renamed"})
    assert updated.json()["name"] == "Renamed"

    assert client.delete(f"/api/v1/workflows/{wf_id}").status_code == 200
    assert client.get(f"/api/v1/workflows/{wf_id}").status_code == 404


def test_workflow_templates_are_real(client):
    tpls = client.get("/api/v1/workflows/templates")
    assert tpls.status_code == 200
    assert len(tpls.json()) > 0, "templates must not be empty"

    tpl_id = tpls.json()[0]["template_id"]
    made = client.post(f"/api/v1/workflows/templates/{tpl_id}", json={})
    assert made.status_code == 200, made.text
    assert len(made.json()["nodes"]) > 0, "template instance must carry nodes"
    client.delete(f"/api/v1/workflows/{made.json()['id']}")


def test_crew_crud(client):
    created = client.post("/api/v1/crews", json={"name": "E2E Crew", "tasks": [{"description": "say hi"}]})
    assert created.status_code == 200, created.text
    crew_id = created.json()["id"]
    assert crew_id != "crew-1"

    assert any(c["id"] == crew_id for c in client.get("/api/v1/crews").json())
    assert client.delete(f"/api/v1/crews/{crew_id}").status_code == 200


def test_skill_lifecycle(client):
    created = client.post("/api/v1/skills", json={"name": "E2E Skill"})
    assert created.status_code == 200, created.text
    sid = created.json()["id"]

    assert client.post(f"/api/v1/skills/{sid}/disable").json()["is_enabled"] is False
    assert client.post(f"/api/v1/skills/{sid}/enable").json()["is_enabled"] is True
    # State must actually persist
    assert next(s for s in client.get("/api/v1/skills").json() if s["id"] == sid)["is_enabled"] is True

    assert client.post("/api/v1/skills/nonexistent/enable").status_code == 404
    client.delete(f"/api/v1/skills/{sid}")


def test_plugin_install_enable_uninstall(client):
    market = client.get("/api/v1/plugins/marketplace")
    assert market.status_code == 200
    assert len(market.json()) > 0
    key = market.json()[0]["plugin_key"]

    installed = client.post(f"/api/v1/plugins/{key}/install", json={})
    assert installed.status_code == 200, installed.text
    pid = installed.json()["id"]

    assert any(p["id"] == pid for p in client.get("/api/v1/plugins").json())
    assert client.post(f"/api/v1/plugins/{pid}/enable").json()["is_enabled"] is True
    assert client.get(f"/api/v1/plugins/{pid}/status").json()["status"] == "enabled"

    assert client.delete(f"/api/v1/plugins/{pid}").status_code == 200
    assert client.get(f"/api/v1/plugins/{pid}/status").status_code == 404


def test_cluster_node_crud(client):
    created = client.post("/api/v1/cluster", json={"name": "node-1", "endpoint": "http://localhost:9000"})
    assert created.status_code == 200, created.text
    nid = created.json()["id"]
    assert nid != "cluster-1"

    status = client.get("/api/v1/cluster/status")
    assert status.json()["total_nodes"] >= 1
    client.delete(f"/api/v1/cluster/{nid}")


def test_stats_reports_real_counts(client):
    client.post("/api/v1/agents", json={"name": "StatAgent"})
    stats = client.get("/api/v1/stats")
    assert stats.status_code == 200
    body = stats.json()
    assert body["total_agents"] >= 1, "stats must reflect real rows"
    for key in ("total_sessions", "total_messages", "total_tokens"):
        assert key in body


def test_tools_endpoint_returns_registered_tools(client):
    tools = client.get("/api/v1/tools")
    assert tools.status_code == 200
    names = [t["name"] for t in tools.json()]
    assert "calculator" in names and "read_file" in names
    assert len(names) >= 20


def test_trailing_slash_variants_resolve(client):
    """These returned hard 404s before; the frontend calls them with slashes."""
    for path in ("/api/v1/workflows/", "/api/v1/crews/", "/api/v1/traces/", "/api/v1/plugins/", "/api/v1/agents/"):
        assert client.get(path).status_code == 200, f"{path} must not 404"


def test_no_stub_hardcoded_ids_remain(client):
    """Guard against regression to hardcoded stub responses."""
    a = client.post("/api/v1/agents", json={"name": "guard"}).json()
    w = client.post("/api/v1/workflows", json={"name": "guard"}).json()
    c = client.post("/api/v1/crews", json={"name": "guard"}).json()
    assert a["id"] not in ("agent-1",) and w["id"] not in ("workflow-1",) and c["id"] not in ("crew-1",)
    client.delete(f"/api/v1/agents/{a['id']}")
    client.delete(f"/api/v1/workflows/{w['id']}")
    client.delete(f"/api/v1/crews/{c['id']}")

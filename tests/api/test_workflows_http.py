"""HTTP-level tests for ``/api/v1/workflows/*``.

The kill-switch case is the one that matters most here: ``WorkflowEngine.execute``
short-circuits to ``status="emergency_stop"`` before touching a model, so the
endpoint can be driven end to end with no provider credentials at all.
"""

from __future__ import annotations

import pytest

from tests.api.conftest import admin_bearer, bearer

BASE = "/api/v1/workflows"

# A single-node graph: start -> end, which the engine can order topologically.
NODES = [
    {"id": "n1", "type": "start", "position": {"x": 0, "y": 0}, "data": {}},
    {"id": "n2", "type": "end", "position": {"x": 200, "y": 0}, "data": {}},
]
EDGES = [{"id": "e1", "source": "n1", "target": "n2", "type": "sequence"}]


async def _seed_agent(user_id: str = "default-user", agent_id: str = "wf-agent-1") -> None:
    from app.storage import async_session
    from app.storage.database import Agent

    async with async_session() as db:
        db.add(
            Agent(
                id=agent_id,
                user_id=user_id,
                name="workflow agent",
                provider="openai",
                model_id="gpt-4o-mini",
            )
        )
        await db.commit()


# --- CRUD --------------------------------------------------------------------


async def test_create_read_update_delete_round_trip(http) -> None:
    created = await http.post(
        f"{BASE}", json={"name": "http wf", "description": "d", "nodes": NODES, "edges": EDGES}
    )

    assert created.status_code == 200
    body = created.json()
    assert body["name"] == "http wf"
    assert body["is_template"] is False
    assert body["run_count"] == 0
    wf_id = body["id"]

    fetched = await http.get(f"{BASE}/{wf_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == wf_id

    listed = await http.get(f"{BASE}")
    assert wf_id in [w["id"] for w in listed.json()]

    updated = await http.put(f"{BASE}/{wf_id}", json={"name": "renamed", "description": "d2"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "renamed"
    assert updated.json()["description"] == "d2"

    deleted = await http.delete(f"{BASE}/{wf_id}")
    assert deleted.status_code == 200
    assert deleted.json() == {"ok": True, "deleted": wf_id}
    assert (await http.get(f"{BASE}/{wf_id}")).status_code == 404


async def test_create_defaults_the_name(http) -> None:
    resp = await http.post(f"{BASE}", json={})

    assert resp.status_code == 200
    assert resp.json()["name"] == "Untitled Workflow"


async def test_update_leaves_unsupplied_fields_alone(http) -> None:
    wf_id = (
        await http.post(
            f"{BASE}", json={"name": "keep me", "description": "keep this too", "nodes": NODES}
        )
    ).json()["id"]

    resp = await http.put(f"{BASE}/{wf_id}", json={"name": "only the name"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "only the name"
    assert body["description"] == "keep this too"
    assert body["nodes"] == NODES


async def test_unknown_workflow_is_404(http) -> None:
    assert (await http.get(f"{BASE}/nope")).status_code == 404
    assert (await http.put(f"{BASE}/nope", json={"name": "x"})).status_code == 404
    assert (await http.delete(f"{BASE}/nope")).status_code == 404


async def test_workflows_are_scoped_to_their_owner(http, auth_on) -> None:
    owner = bearer("owner-user")
    wf_id = (await http.post(f"{BASE}", json={"name": "private"}, headers=owner)).json()["id"]
    other = bearer("intruder-user")

    assert (await http.get(f"{BASE}/{wf_id}", headers=other)).status_code == 404
    assert (await http.put(f"{BASE}/{wf_id}", json={"name": "hijack"}, headers=other)).status_code == 404
    assert (await http.delete(f"{BASE}/{wf_id}", headers=other)).status_code == 404
    assert wf_id not in [w["id"] for w in (await http.get(f"{BASE}", headers=other)).json()]


async def test_workflow_endpoints_require_credentials_when_auth_enabled(http, auth_on) -> None:
    assert (await http.get(f"{BASE}")).status_code == 401
    assert (await http.post(f"{BASE}", json={"name": "x"})).status_code == 401


# --- run ---------------------------------------------------------------------


async def test_run_422s_when_the_graph_has_no_nodes(http) -> None:
    wf_id = (await http.post(f"{BASE}", json={"name": "empty"})).json()["id"]

    resp = await http.post(f"{BASE}/{wf_id}/run", json={})

    assert resp.status_code == 422
    assert resp.json()["detail"] == "Workflow has no nodes to execute"


async def test_run_422s_when_the_caller_has_no_agent(http) -> None:
    wf_id = (await http.post(f"{BASE}", json={"name": "wf", "nodes": NODES})).json()["id"]

    resp = await http.post(f"{BASE}/{wf_id}/run", json={})

    assert resp.status_code == 422
    assert "agent" in resp.json()["detail"].lower()


async def test_run_refuses_a_node_pointing_at_another_users_agent(http, auth_on) -> None:
    await _seed_agent(user_id="owner-user", agent_id="owned-agent")
    nodes = [
        {"id": "n1", "type": "start", "position": {"x": 0, "y": 0}, "data": {"agent_id": "owned-agent"}},
        {"id": "n2", "type": "end", "position": {"x": 200, "y": 0}, "data": {}},
    ]
    wf_id = (await http.post(f"{BASE}", json={"name": "borrowed"}, headers=bearer("owner-user"))).json()["id"]

    resp = await http.post(
        f"{BASE}/{wf_id}/run", json={"nodes": nodes}, headers=bearer("intruder-user")
    )

    assert resp.status_code == 422
    assert resp.json()["detail"] == "Workflow agent_id must reference an owned agent"


async def test_run_reports_the_emergency_stop_status(http, auth_on) -> None:
    """An armed kill switch must surface as ``emergency_stop``, not a 200 success."""
    await _seed_agent(user_id="admin-user", agent_id="stop-agent")
    wf_id = (
        await http.post(
            f"{BASE}", json={"name": "blocked wf", "nodes": NODES}, headers=admin_bearer()
        )
    ).json()["id"]
    armed = await http.post(
        "/api/v1/observability/emergency-stop",
        json={"reason": "test kill switch"},
        headers=admin_bearer(),
    )
    assert armed.status_code == 200

    resp = await http.post(f"{BASE}/{wf_id}/run", json={}, headers=admin_bearer())

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "emergency_stop"
    assert body["outputs"] == {}
    assert body["node_results"] == {}
    assert body["error"]


async def test_run_reports_why_the_kill_switch_refused(http, auth_on) -> None:
    await _seed_agent(user_id="admin-user", agent_id="reason-agent")
    wf_id = (
        await http.post(
            f"{BASE}", json={"name": "reason wf", "nodes": NODES}, headers=admin_bearer()
        )
    ).json()["id"]
    await http.post(
        "/api/v1/observability/emergency-stop",
        json={"reason": "p99 breach in prod", "triggered_by": "oncall"},
        headers=admin_bearer(),
    )

    resp = await http.post(f"{BASE}/{wf_id}/run", json={}, headers=admin_bearer())

    assert resp.status_code == 200
    assert "p99 breach in prod" in resp.json()["error"]


async def test_run_reports_the_emergency_stop_status_for_an_ad_hoc_graph(http, auth_on) -> None:
    """A graph supplied in the body must be gated by the same kill switch."""
    await _seed_agent(user_id="admin-user", agent_id="adhoc-agent")
    await http.post(
        "/api/v1/observability/emergency-stop",
        json={"reason": "adhoc block"},
        headers=admin_bearer(),
    )

    resp = await http.post(
        f"{BASE}/whatever/run",
        json={"nodes": NODES, "edges": EDGES},
        headers=admin_bearer(),
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "emergency_stop"
    assert resp.json()["error"]


async def test_run_is_recorded_in_the_workflow_run_history(http, auth_on) -> None:
    await _seed_agent(user_id="admin-user", agent_id="history-agent")
    wf_id = (
        await http.post(
            f"{BASE}", json={"name": "recorded", "nodes": NODES}, headers=admin_bearer()
        )
    ).json()["id"]
    await http.post(
        "/api/v1/observability/emergency-stop",
        json={"reason": "history test"},
        headers=admin_bearer(),
    )
    await http.post(f"{BASE}/{wf_id}/run", json={}, headers=admin_bearer())

    resp = await http.get(f"{BASE}/{wf_id}/runs", headers=admin_bearer())

    assert resp.status_code == 200
    runs = resp.json()
    assert len(runs) == 1
    assert runs[0]["status"] == "emergency_stop"


async def test_run_history_of_an_unknown_workflow_is_404(http) -> None:
    resp = await http.get(f"{BASE}/nope/runs")

    assert resp.status_code == 404


async def test_delete_also_drops_the_run_history(http, auth_on) -> None:
    await _seed_agent(user_id="admin-user", agent_id="cascade-agent")
    wf_id = (
        await http.post(
            f"{BASE}", json={"name": "cascade", "nodes": NODES}, headers=admin_bearer()
        )
    ).json()["id"]
    await http.post(
        "/api/v1/observability/emergency-stop",
        json={"reason": "cascade"},
        headers=admin_bearer(),
    )
    await http.post(f"{BASE}/{wf_id}/run", json={}, headers=admin_bearer())
    runs = (await http.get(f"{BASE}/{wf_id}/runs", headers=admin_bearer())).json()
    assert len(runs) == 1

    assert (await http.delete(f"{BASE}/{wf_id}", headers=admin_bearer())).status_code == 200
    assert (await http.get(f"{BASE}/{wf_id}/runs", headers=admin_bearer())).status_code == 404


@pytest.mark.parametrize("path", ["", "/"])
async def test_list_accepts_both_slash_spellings(http, path) -> None:
    resp = await http.get(f"{BASE}{path}")

    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

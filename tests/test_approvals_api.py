"""Tests for the approvals API endpoints via TestClient."""

from __future__ import annotations

import pytest

import app.core.approval as approval_module
from app.core.approval import ApprovalManager
from app.core.auth import get_current_user
from app.main import app


@pytest.fixture(autouse=True)
def _fresh_manager(monkeypatch: pytest.MonkeyPatch):
    """Replace the module singleton with a fresh manager per test.

    approvals.py binds the singleton at import time, so both module references
    must be patched.
    """
    manager = ApprovalManager()
    monkeypatch.setattr(approval_module, "approval_manager", manager)
    monkeypatch.setattr("app.api.v1.approvals.approval_manager", manager)
    return manager


async def _create_request(manager: ApprovalManager, user_id: str = "default-user") -> str:
    req = await manager.request(
        session_id="session-test",
        tool_name="run_command",
        arguments={"command": "ls"},
        user_id=user_id,
    )
    return req.id


@pytest.mark.asyncio
async def test_list_approvals_empty(client):
    resp = await client.get("/api/v1/approvals/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["requests"] == []


@pytest.mark.asyncio
async def test_list_approvals_with_pending(client, _fresh_manager):
    req_id = await _create_request(_fresh_manager)
    resp = await client.get("/api/v1/approvals/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["requests"][0]["id"] == req_id
    assert data["requests"][0]["status"] == "pending"
    assert data["requests"][0]["tool_name"] == "run_command"


@pytest.mark.asyncio
async def test_list_approvals_filter_by_session(client, _fresh_manager):
    await _create_request(_fresh_manager)
    resp = await client.get("/api/v1/approvals/?session_id=other-session")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_approve_request(client, _fresh_manager):
    req_id = await _create_request(_fresh_manager)
    resp = await client.post("/api/v1/approvals/approve", json={"request_id": req_id})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["request"]["status"] == "approved"
    assert body["request"]["resolved_by"] == "human"


@pytest.mark.asyncio
async def test_approve_missing_request_returns_404(client, _fresh_manager):
    resp = await client.post("/api/v1/approvals/approve", json={"request_id": "does-not-exist"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_reject_request(client, _fresh_manager):
    req_id = await _create_request(_fresh_manager)
    resp = await client.post("/api/v1/approvals/reject", json={"request_id": req_id, "reason": "not allowed"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["request"]["status"] == "rejected"
    assert body["request"]["reason"] == "not allowed"


@pytest.mark.asyncio
async def test_reject_then_approve_second_returns_404(client, _fresh_manager):
    req_id = await _create_request(_fresh_manager)
    await client.post("/api/v1/approvals/reject", json={"request_id": req_id})
    resp = await client.post("/api/v1/approvals/approve", json={"request_id": req_id})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_all_requests(client, _fresh_manager):
    req_id = await _create_request(_fresh_manager)
    await client.post("/api/v1/approvals/approve", json={"request_id": req_id})
    resp = await client.get("/api/v1/approvals/requests")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["requests"][0]["status"] == "approved"


@pytest.mark.asyncio
async def test_list_all_requests_total_is_independent_of_limit(client, _fresh_manager):
    first_id = await _create_request(_fresh_manager)
    await _create_request(_fresh_manager)
    await client.post("/api/v1/approvals/approve", json={"request_id": first_id})

    resp = await client.get("/api/v1/approvals/requests?limit=1")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["requests"]) == 1
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_list_all_requests_rejects_unbounded_limit(client):
    resp = await client.get("/api/v1/approvals/requests?limit=0")

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_approval_endpoints_are_isolated_by_current_user(client, _fresh_manager):
    own_id = await _create_request(_fresh_manager, user_id="user-a")
    other_id = await _create_request(_fresh_manager, user_id="user-b")
    app.dependency_overrides[get_current_user] = lambda: "user-a"
    try:
        pending = await client.get("/api/v1/approvals/")
        history = await client.get("/api/v1/approvals/requests")
        forbidden = await client.post(
            "/api/v1/approvals/approve",
            json={"request_id": other_id},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert pending.status_code == 200
    assert [request["id"] for request in pending.json()["requests"]] == [own_id]
    assert history.status_code == 200
    assert history.json()["total"] == 1
    assert [request["id"] for request in history.json()["requests"]] == [own_id]
    assert forbidden.status_code == 404

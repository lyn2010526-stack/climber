"""HTTP-level tests for ``/api/v1/permissions/*``.

Covers the approval endpoint's decision vocabulary, its not-found and
bad-request paths, admin enforcement on the config mutation, and a recorded
cross-identity defect on ``/resolve`` (see the xfail marker for the reason).
"""

from __future__ import annotations

import asyncio

import pytest

from app.api.v1.chat import get_engine
from tests.api.conftest import admin_bearer, bearer


@pytest.fixture
def engine_with_pending_request():
    """Register a session holding one pending permission request.

    ``AgentEngine.resolve_permission`` scans ``engine._sessions`` for a matching
    ``tool_call_id``, so this reproduces exactly the state a tool call blocked on
    an approval prompt would leave behind.
    """
    from app.api.v1.chat import get_engine

    engine = get_engine()
    session = engine.create_session(
        agent_id="perm-agent",
        user_id="owner-user",
        provider="openai",
        model_id="gpt-4o-mini",
        api_key="sk-not-a-real-key",
        session_id="perm-session-1",
    )
    session._permission_event = asyncio.Event()
    session._pending_permission = {"tool_call_id": "call-1", "decision": None}
    yield engine, session, "call-1"
    engine.close_session("perm-session-1")


@pytest.fixture
def isolated_permission_config():
    """Restore the process-wide default permission config after a mutation.

    ``AgentEngine._default_permission_config`` is a singleton the ``PUT /config``
    handler replaces, so without this a rewritten rule set would leak into every
    later test in the session.
    """
    from app.api.v1.chat import get_engine

    engine = get_engine()
    original = engine.get_permission_config()
    yield engine
    engine._default_permission_config = original


# --- /resolve ----------------------------------------------------------------


async def test_resolve_returns_the_recorded_decision(http, engine_with_pending_request) -> None:
    engine, session, call_id = engine_with_pending_request

    resp = await http.post(
        "/api/v1/permissions/resolve", json={"tool_call_id": call_id, "decision": "allow"}
    )

    assert resp.status_code == 200
    assert resp.json() == {"status": "resolved", "tool_call_id": call_id, "decision": "allow"}
    # The decision must land on the live session, not only in the response body.
    assert session._pending_permission["decision"] == "allow"
    assert engine._sessions["perm-session-1"] is session


@pytest.mark.parametrize("decision", ["allow", "allow_session", "allow_always", "deny"])
async def test_resolve_accepts_every_documented_decision(
    http, engine_with_pending_request, decision
) -> None:
    _engine, session, call_id = engine_with_pending_request

    resp = await http.post(
        "/api/v1/permissions/resolve", json={"tool_call_id": call_id, "decision": decision}
    )

    assert resp.status_code == 200
    assert resp.json()["decision"] == decision
    assert session._pending_permission["decision"] == decision


async def test_resolve_rejects_an_unknown_decision(http, engine_with_pending_request) -> None:
    _engine, _session, call_id = engine_with_pending_request

    resp = await http.post(
        "/api/v1/permissions/resolve", json={"tool_call_id": call_id, "decision": "maybe"}
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid decision: maybe"


async def test_resolve_404s_for_an_unknown_tool_call(http) -> None:
    resp = await http.post(
        "/api/v1/permissions/resolve",
        json={"tool_call_id": "call-does-not-exist", "decision": "allow"},
    )

    assert resp.status_code == 404
    assert "call-does-not-exist" in resp.json()["detail"]


async def test_resolve_validates_the_request_body(http) -> None:
    resp = await http.post("/api/v1/permissions/resolve", json={"decision": "allow"})

    assert resp.status_code == 422


async def test_resolve_requires_an_authenticated_caller_when_auth_enabled(http, auth_on) -> None:
    resp = await http.post(
        "/api/v1/permissions/resolve", json={"tool_call_id": "c", "decision": "deny"}
    )

    assert resp.status_code == 401
    assert resp.json()["type"] == "authentication_required"


async def test_resolve_releases_the_awaiting_session(http, engine_with_pending_request) -> None:
    """Resolving over HTTP must wake the coroutine parked in the approval wait."""
    _engine, session, call_id = engine_with_pending_request

    assert not session._permission_event.is_set()

    resp = await http.post(
        "/api/v1/permissions/resolve", json={"tool_call_id": call_id, "decision": "deny"}
    )
    await asyncio.sleep(0)

    assert resp.status_code == 200
    assert session._permission_event.is_set()
    assert session._pending_permission["decision"] == "deny"


async def test_resolve_across_sessions_is_forbidden(
    http, auth_on, engine_with_pending_request
) -> None:
    """Approving a tool call parked on another user's session is an escalation."""
    _engine, session, call_id = engine_with_pending_request

    resp = await http.post(
        "/api/v1/permissions/resolve",
        json={"tool_call_id": call_id, "decision": "allow_always"},
        headers=bearer("intruder-user", ["read", "write"]),
    )

    assert resp.status_code == 403
    assert session._pending_permission["decision"] != "allow_always"


# --- /config -----------------------------------------------------------------


async def test_config_get_returns_mode_rules_and_tool_lists(http) -> None:
    resp = await http.get("/api/v1/permissions/config")

    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"mode", "rules", "allowed_tools", "denied_tools"}
    assert isinstance(body["mode"], str)
    assert isinstance(body["rules"], list)


async def test_config_get_requires_authentication_when_auth_enabled(http, auth_on) -> None:
    resp = await http.get("/api/v1/permissions/config")

    assert resp.status_code == 401
    assert resp.json()["type"] == "authentication_required"


async def test_config_get_allows_an_authenticated_caller(http, auth_on) -> None:
    resp = await http.get("/api/v1/permissions/config", headers=bearer("reader"))

    assert resp.status_code == 200
    assert set(resp.json()) == {"mode", "rules", "allowed_tools", "denied_tools"}


async def test_config_put_applies_the_new_rules_to_the_engine(
    http, isolated_permission_config
) -> None:
    resp = await http.put(
        "/api/v1/permissions/config",
        json={
            "mode": "acceptEdits",
            "rules": [
                {
                    "decision": "deny",
                    "tool": "run_command",
                    "pattern": "rm *",
                    "description": "no destructive shell",
                }
            ],
            "allowed_tools": ["web_search"],
            "denied_tools": ["file_delete"],
        },
    )

    assert resp.status_code == 200
    assert resp.json() == {"status": "updated", "mode": "acceptEdits"}

    stored = get_engine().get_permission_config()
    assert stored.mode.value == "acceptEdits"
    assert [(r.decision.value, r.tool, r.pattern) for r in stored.rules] == [
        ("deny", "run_command", "rm *")
    ]
    assert stored.allowed_tools == ["web_search"]
    assert stored.denied_tools == ["file_delete"]

    read_back = await http.get("/api/v1/permissions/config")
    assert read_back.json()["rules"][0]["tool"] == "run_command"
    assert read_back.json()["denied_tools"] == ["file_delete"]


async def test_config_put_rejects_an_invalid_mode(http, isolated_permission_config) -> None:
    resp = await http.put("/api/v1/permissions/config", json={"mode": "yolo"})

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid mode: yolo"


async def test_config_put_rejects_an_invalid_rule_decision(
    http, isolated_permission_config
) -> None:
    resp = await http.put(
        "/api/v1/permissions/config",
        json={"rules": [{"decision": "perhaps", "tool": "run_command"}]},
    )

    assert resp.status_code == 400
    assert "perhaps" in resp.json()["detail"]


async def test_config_put_keeps_unsupplied_fields_when_merging(
    http, isolated_permission_config
) -> None:
    """A partial update must preserve the fields the body leaves out."""
    before = (await http.get("/api/v1/permissions/config")).json()
    rules_before = len(before["rules"])

    resp = await http.put("/api/v1/permissions/config", json={"denied_tools": ["file_delete"]})

    assert resp.status_code == 200
    after = (await http.get("/api/v1/permissions/config")).json()
    assert after["denied_tools"] == ["file_delete"]
    assert after["mode"] == before["mode"]
    assert after["allowed_tools"] == before["allowed_tools"]
    assert len(after["rules"]) == rules_before


async def test_config_put_is_refused_for_a_non_admin_when_auth_enabled(http, auth_on) -> None:
    before = (await http.get("/api/v1/permissions/config", headers=bearer("u"))).json()

    resp = await http.put(
        "/api/v1/permissions/config",
        json={"denied_tools": ["file_delete"]},
        headers=bearer("plain-user", ["read", "write"]),
    )

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Admin scope required"
    after = (await http.get("/api/v1/permissions/config", headers=bearer("plain-user"))).json()
    assert after == before


async def test_config_put_is_allowed_for_an_admin_when_auth_enabled(
    http, auth_on, isolated_permission_config
) -> None:
    resp = await http.put(
        "/api/v1/permissions/config",
        json={"denied_tools": ["file_delete"]},
        headers=admin_bearer(),
    )

    assert resp.status_code == 200
    body = (await http.get("/api/v1/permissions/config", headers=admin_bearer())).json()
    assert body["denied_tools"] == ["file_delete"]

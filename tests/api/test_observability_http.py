"""HTTP-level tests for ``/api/v1/observability/*``.

The emergency-stop endpoints are the only admin-gated mutations on this router and
the kill switch they drive is process-wide, so each test gets a private store from
the ``isolated_emergency_stop`` fixture in ``tests/api/conftest.py``. The read
endpoints are asserted for the shape a dashboard actually renders.
"""

from __future__ import annotations

import pytest

from tests.api.conftest import admin_bearer, bearer

BASE = "/api/v1/observability"


async def _is_active(http, headers) -> bool:
    resp = await http.get(f"{BASE}/emergency-stop", headers=headers)
    assert resp.status_code == 200
    return resp.json()["is_activated"]


# --- emergency stop: admin gate ---------------------------------------------


async def test_activation_requires_an_admin(http, auth_on) -> None:
    resp = await http.post(
        f"{BASE}/emergency-stop",
        json={"reason": "test"},
        headers=bearer("plain-user", ["read", "write"]),
    )

    assert resp.status_code == 403
    assert "admin" in resp.json()["detail"].lower()
    # The refused activation must not have armed the kill switch.
    assert await _is_active(http, admin_bearer()) is False


async def test_activation_requires_credentials_when_auth_enabled(http, auth_on) -> None:
    resp = await http.post(f"{BASE}/emergency-stop", json={"reason": "test"})

    assert resp.status_code == 401
    assert await _is_active(http, admin_bearer()) is False


async def test_admin_can_activate_and_deactivate(http, auth_on) -> None:
    headers = admin_bearer()

    resp = await http.post(
        f"{BASE}/emergency-stop",
        json={"reason": "kill switch", "triggered_by": "ops"},
        headers=headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "activated"
    assert body["record"]["action"] == "activate"
    assert body["record"]["reason"] == "kill switch"
    assert body["record"]["triggered_by"] == "ops"
    assert body["record"]["timestamp"]
    assert body["record"]["auto_trigger"] is False

    status = await http.get(f"{BASE}/emergency-stop", headers=headers)
    assert status.status_code == 200
    assert status.json()["is_activated"] is True
    assert status.json()["reason"] == "kill switch"
    assert status.json()["activated_by"] == "ops"
    assert status.json()["activated_at"]

    off = await http.delete(f"{BASE}/emergency-stop", headers=headers)
    assert off.status_code == 200
    assert off.json()["status"] == "deactivated"
    assert off.json()["record"]["action"] == "deactivate"
    assert await _is_active(http, headers) is False


async def test_double_activation_conflicts(http, auth_on) -> None:
    headers = admin_bearer()
    await http.post(f"{BASE}/emergency-stop", json={"reason": "first"}, headers=headers)

    second = await http.post(
        f"{BASE}/emergency-stop", json={"reason": "second"}, headers=headers
    )

    assert second.status_code == 409
    assert second.json()["detail"] == "Emergency stop is already activated"
    # The first reason must survive the rejected second attempt.
    assert (await http.get(f"{BASE}/emergency-stop", headers=headers)).json()["reason"] == "first"


async def test_deactivating_an_inactive_stop_conflicts(http, auth_on) -> None:
    resp = await http.delete(f"{BASE}/emergency-stop", headers=admin_bearer())

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Emergency stop is not activated"


async def test_deactivation_requires_an_admin(http, auth_on) -> None:
    headers = admin_bearer()
    await http.post(f"{BASE}/emergency-stop", json={"reason": "armed"}, headers=headers)

    resp = await http.delete(
        f"{BASE}/emergency-stop", headers=bearer("plain-user", ["read", "write"])
    )

    assert resp.status_code == 403
    # A refused deactivation must leave the kill switch armed.
    assert await _is_active(http, headers) is True


async def test_status_is_readable_without_the_admin_scope(http, auth_on) -> None:
    resp = await http.get(f"{BASE}/emergency-stop", headers=bearer("reader", ["read"]))

    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"is_activated", "reason", "activated_by", "activated_at"}
    assert body["is_activated"] is False


async def test_deactivation_accepts_an_optional_body(http, auth_on) -> None:
    headers = admin_bearer()
    await http.post(f"{BASE}/emergency-stop", json={"reason": "armed"}, headers=headers)

    resp = await http.request(
        "DELETE", f"{BASE}/emergency-stop", headers=headers, json={"reason": "all clear"}
    )

    assert resp.status_code == 200
    assert resp.json()["record"]["reason"] == "all clear"


async def test_activation_defaults_reason_and_actor(http, auth_on) -> None:
    resp = await http.post(f"{BASE}/emergency-stop", json={}, headers=admin_bearer())

    assert resp.status_code == 200
    assert resp.json()["record"]["reason"] == "manual activation"
    assert resp.json()["record"]["triggered_by"] == "user"


# --- traces ------------------------------------------------------------------


async def test_trace_list_reports_the_paging_window(http, auth_on) -> None:
    resp = await http.get(f"{BASE}/traces?limit=5&offset=0", headers=bearer("r", ["read"]))

    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"traces", "limit", "offset"}
    assert body["limit"] == 5
    assert body["offset"] == 0
    assert isinstance(body["traces"], list)


@pytest.mark.parametrize("query", ["limit=0", "limit=201", "offset=-1"])
async def test_trace_paging_rejects_out_of_range_values(http, auth_on, query) -> None:
    resp = await http.get(f"{BASE}/traces?{query}", headers=bearer("r", ["read"]))

    assert resp.status_code == 422


async def test_unknown_trace_is_404(http, auth_on) -> None:
    resp = await http.get(
        f"{BASE}/traces/trace-that-does-not-exist", headers=bearer("r", ["read"])
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Trace not found"


# --- audit -------------------------------------------------------------------


async def test_audit_entries_report_a_total_and_window(http, auth_on) -> None:
    resp = await http.get(f"{BASE}/audit?limit=10&offset=0", headers=bearer("r", ["read"]))

    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"entries", "total", "limit", "offset"}
    assert isinstance(body["total"], int)
    assert isinstance(body["entries"], list)


async def test_audit_accepts_a_decision_type_filter(http, auth_on) -> None:
    resp = await http.get(f"{BASE}/audit?decision_type=tool_call", headers=bearer("r", ["read"]))

    assert resp.status_code == 200
    assert isinstance(resp.json()["entries"], list)


async def test_audit_requires_credentials_when_auth_enabled(http, auth_on) -> None:
    resp = await http.get(f"{BASE}/audit")

    assert resp.status_code == 401


# --- alignment ---------------------------------------------------------------


async def test_alignment_reports_goals_drift_and_threshold(http, auth_on) -> None:
    resp = await http.get(f"{BASE}/alignment", headers=bearer("r", ["read"]))

    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"goals", "drift_score", "threshold"}
    assert isinstance(body["goals"], list)
    assert isinstance(body["drift_score"], (int, float))
    assert body["threshold"] > 0

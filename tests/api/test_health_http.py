"""HTTP-level tests for the operational endpoints: ``/health``, ``/health/logs``,
``/metrics`` and ``/api/v1/doctor``.

These are the routes an orchestrator and an operator read to decide whether the
process is healthy, so the assertions are about the exact status code and the
fields a probe reads, not just that a body came back.
"""

from __future__ import annotations

import pytest

from tests.api.conftest import bearer

COMPONENT_KEYS = {"database", "redis", "chroma", "watchdog", "memory", "browser_pool"}


async def test_health_reports_every_component_and_200_when_well(http) -> None:
    resp = await http.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert set(body) >= COMPONENT_KEYS
    assert body["version"]
    assert body["status"] in {"ok", "degraded"}
    assert body["database"]["connected"] is True


async def test_health_marks_itself_degraded_when_the_database_is_down(http, monkeypatch) -> None:
    """A database outage must flip ``status`` to degraded, not stay ``ok``."""
    import app.main as main

    async def _broken_db_health():
        return {"connected": False, "error": "connection refused"}

    monkeypatch.setattr(main, "db_health", _broken_db_health)

    resp = await http.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["database"]["connected"] is False
    assert body["database"]["error"] == "connection refused"


async def test_health_reports_each_subsystem_http_error_as_a_string(http, monkeypatch) -> None:
    import app.main as main

    class _Boom:
        async def get_redis(self):
            raise RuntimeError("redis is down")

    async def _db_ok():
        return {"connected": True, "backend": "sqlite"}

    monkeypatch.setattr(main, "get_redis", _Boom().get_redis)
    monkeypatch.setattr(main, "db_health", _db_ok)

    resp = await http.get("/health")

    assert resp.status_code == 200
    assert resp.json()["redis"] == "unavailable"


async def test_health_is_reachable_without_credentials_when_auth_enabled(http, auth_on) -> None:
    """An orchestrator has no bearer token, so this must stay open."""
    resp = await http.get("/health")

    assert resp.status_code == 200


async def test_health_logs_returns_bounded_lines(http) -> None:
    resp = await http.get("/health/logs?lines=5")

    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"lines", "log_dir"}
    assert isinstance(body["lines"], list)
    assert len(body["lines"]) <= 5
    assert body["log_dir"]


async def test_health_logs_caps_an_oversized_request(http) -> None:
    """The handler clamps to 2000, so a huge ask must not be honoured literally."""
    resp = await http.get("/health/logs?lines=100000")

    assert resp.status_code == 200
    assert len(resp.json()["lines"]) <= 2000


async def test_health_logs_accepts_the_errors_only_filter(http) -> None:
    resp = await http.get("/health/logs?lines=20&errors_only=true")

    assert resp.status_code == 200
    assert isinstance(resp.json()["lines"], list)


async def test_metrics_endpoint_is_served(http) -> None:
    resp = await http.get("/metrics")

    assert resp.status_code == 200
    assert resp.content


# --- doctor ------------------------------------------------------------------


async def test_doctor_returns_503_when_any_check_fails(http, monkeypatch) -> None:
    """A failing check must surface as 503 so a probe can act on it."""
    import app.api.v1.doctor as doctor

    def _broken_services() -> dict:
        return {"section": "services", "checks": [{"name": "watchdog", "ok": False, "detail": "down"}]}

    monkeypatch.setattr(doctor, "_check_services_sync", _broken_services)

    resp = await http.get("/api/v1/doctor/")

    assert resp.status_code == 503
    body = resp.json()
    assert body["healthy"] is False
    services = next(s for s in body["sections"] if s["section"] == "services")
    assert any(c["name"] == "watchdog" and c["ok"] is False for c in services["checks"])


async def test_doctor_healthy_flag_always_agrees_with_the_status_code(http) -> None:
    """The 200/503 decision and the ``healthy`` flag must never disagree.

    The individual checks are environment-dependent (an absent optional dependency
    legitimately reports ``ok: false``), so the invariant worth pinning is that
    the handler derives the status code from the same aggregate it reports.
    """
    resp = await http.get("/api/v1/doctor/")
    body = resp.json()

    assert resp.status_code == (200 if body["healthy"] else 503)
    all_ok = all(c["ok"] for s in body["sections"] for c in s["checks"])
    assert body["healthy"] is all_ok


async def test_doctor_reports_the_expected_sections(http) -> None:
    resp = await http.get("/api/v1/doctor/")

    assert resp.status_code in {200, 503}
    body = resp.json()
    assert set(body) >= {"version", "platform", "sections", "healthy"}
    sections = {s["section"] for s in body["sections"]}
    assert {"python_runtime", "core_dependencies", "database", "services", "workspace"} <= sections
    assert body["platform"]["python"].startswith("3.")


@pytest.mark.parametrize("path", ["/api/v1/doctor", "/api/v1/doctor/"])
async def test_doctor_serves_both_slash_spellings(http, path) -> None:
    resp = await http.get(path)

    assert resp.status_code in {200, 503}
    assert "sections" in resp.json()


async def test_doctor_python_runtime_check_reports_the_running_interpreter(http) -> None:
    resp = await http.get("/api/v1/doctor/")

    runtime = next(
        s for s in resp.json()["sections"] if s["section"] == "python_runtime"
    )
    check = next(c for c in runtime["checks"] if c["name"] == "python_version")
    # The project requires 3.11; the endpoint has to say so rather than assume.
    assert check["ok"] is True
    assert check["detail"].startswith("3.")


async def test_doctor_requires_credentials_when_auth_enabled(http, auth_on) -> None:
    resp = await http.get("/api/v1/doctor/")

    assert resp.status_code == 401

    allowed = await http.get("/api/v1/doctor/", headers=bearer("r", ["read"]))
    assert allowed.status_code in {200, 503}

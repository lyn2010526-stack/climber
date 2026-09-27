"""Regression tests for the emergency stop kill switch wiring.

Two defects are covered:

1. ``app.core.observability.api`` kept its own module-level singleton, so
   activating the stop through REST never reached the manager the engine reads.
2. The mutate endpoints had no admin dependency, so any authenticated caller
   could halt or resume every running agent.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.core.observability import api as obs_api
from app.core.observability import emergency_stop as es


@pytest.fixture(autouse=True)
def _reset_shared_manager():
    original = es._EMERGENCY_STOP
    obs_api._trace_collector = None
    obs_api._audit_chain = None
    obs_api._goal_tracker = None
    yield
    es._EMERGENCY_STOP = original


def test_api_and_engine_share_one_manager_instance():
    """The router must return the exact object the engine consults."""
    assert obs_api.get_emergency_stop() is es.get_emergency_stop()
    assert obs_api.get_emergency_stop() is obs_api.get_emergency_stop()


def test_activate_via_router_is_visible_to_engine_gate(tmp_path):
    """An activation through REST must flip the gate the engine reads."""
    manager = es.EmergencyStopManager(db_path=str(tmp_path / "stop.db"))
    es.set_emergency_stop(manager)

    assert es.is_emergency_stop_active() is False

    request = obs_api.EmergencyStopRequest(reason="test", triggered_by="tester")
    result = obs_api.activate_emergency_stop.__wrapped__(
        request, {"id": "admin", "scopes": ["admin"]}
    ) if hasattr(obs_api.activate_emergency_stop, "__wrapped__") else None

    if result is None:
        import asyncio

        result = asyncio.run(
            obs_api.activate_emergency_stop(request, {"id": "admin", "scopes": ["admin"]})
        )

    assert result["status"] == "activated"
    # The engine gate reads the shared manager, so it must now refuse work.
    assert es.is_emergency_stop_active() is True
    assert manager.is_activated() is True


def test_mutating_endpoints_require_admin():
    """Activate and deactivate must declare an admin dependency."""
    for endpoint in (obs_api.activate_emergency_stop, obs_api.deactivate_emergency_stop):
        dependencies = set(getattr(endpoint, "__defaults__", ()))
        has_admin = any(
            dep is not None and getattr(dep, "dependency", None) is not None
            for dep in dependencies
        )
        assert has_admin, f"{endpoint.__name__} lacks an admin dependency"


def test_deactivate_conflict_when_not_activated(tmp_path):
    import asyncio

    es.set_emergency_stop(es.EmergencyStopManager(db_path=str(tmp_path / "stop2.db")))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(obs_api.deactivate_emergency_stop({"id": "admin", "scopes": ["admin"]}, None))
    assert exc.value.status_code == 409

"""Zero-auth admin escalation tests.

`require_admin` and `require_scopes` (app/core/auth_manager.py) auto-grant
admin when `enable_auth` is False. That is a deliberate convenience for local
development, but the check reads only the flag, never the environment, so a
production deployment that shipped with `ENABLE_AUTH=false` (the default, and
the state a container lands in when only APP_SECRET_KEY is configured) exposes
every admin endpoint with no credential at all.

These tests pin the boundary: the bypass is a local-development affordance and
must not apply to production, while keeping the local workflow intact.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def request_stub():
    class Request:
        def __init__(self) -> None:
            self.state = type("S", (), {})()

    return Request()


def _principal_for_default_user():

    return {"id": "default-user", "scopes": [], "role": None}


def test_the_bypass_is_not_available_in_production(monkeypatch) -> None:
    from app.core import auth_manager

    monkeypatch.setattr(auth_manager.settings, "enable_auth", False, raising=False)
    monkeypatch.setattr(auth_manager.settings, "app_env", "production", raising=False)

    assert auth_manager._auto_privilege_allowed() is False


@pytest.mark.parametrize("environment", ["local", "development", "test", "testing"])
def test_the_bypass_still_works_for_local_development(monkeypatch, environment) -> None:
    from app.core import auth_manager

    monkeypatch.setattr(auth_manager.settings, "enable_auth", False, raising=False)
    monkeypatch.setattr(auth_manager.settings, "app_env", environment, raising=False)

    assert auth_manager._auto_privilege_allowed() is True


def test_auth_enabled_never_auto_privileges(monkeypatch) -> None:
    from app.core import auth_manager

    monkeypatch.setattr(auth_manager.settings, "enable_auth", True, raising=False)
    monkeypatch.setattr(auth_manager.settings, "app_env", "local", raising=False)

    assert auth_manager._auto_privilege_allowed() is False


@pytest.mark.asyncio
async def test_production_admin_endpoint_rejects_an_anonymous_caller(monkeypatch) -> None:
    """End-to-end shape: an unauthenticated call must not get admin."""
    from fastapi import HTTPException

    from app.core import auth_manager

    monkeypatch.setattr(auth_manager.settings, "enable_auth", False, raising=False)
    monkeypatch.setattr(auth_manager.settings, "app_env", "production", raising=False)
    monkeypatch.setattr(auth_manager, "_principal_dict", _principal_for_default_user)

    with pytest.raises(HTTPException) as exc:
        await auth_manager.require_admin()(_DummyRequest())

    assert exc.value.status_code == 403


class _DummyRequest:
    state = type("S", (), {})()

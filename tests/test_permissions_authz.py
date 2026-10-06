"""Authorization tests for the permission policy endpoints.

`GET /api/v1/permissions/config` returns the enforced mode together with the
full `allowed_tools` / `denied_tools` allow- and deny-lists, so it carries the
same admin gate as the `PUT` write path. These tests pin that gate: anonymous
callers are rejected with 401, authenticated non-admins with 403, and only an
admin identity receives the policy.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from collections.abc import Iterator

# conftest.py normally pins these before `app` is imported; the file also runs
# standalone (`--noconftest`), so the test env is set here as well.
os.environ["APP_TESTING"] = "true"
os.environ["ENABLE_AUTH"] = "false"

from app.api.v1 import permissions as permissions_module
from app.api.v1.permissions import router as permissions_router
from app.config import settings
from app.core.auth_manager import create_access_token
from app.core.permission_rules import (
    PermissionConfig,
    PermissionMode,
    PermissionTier,
    PermissionRule,
    RuleDecision,
)
from app.middleware.auth import AuthMiddleware

CONFIG_PATH = "/api/v1/permissions/config"


class StubEngine:
    """Stands in for the AgentEngine so these routes need no session state."""

    def __init__(self, config: PermissionConfig) -> None:
        self.config = config

    def get_permission_config(self) -> PermissionConfig:
        return self.config

    def update_permission_config(self, config: PermissionConfig) -> None:
        self.config = config


@pytest.fixture
def admin_config() -> PermissionConfig:
    return PermissionConfig(
        mode=PermissionMode.STRICT,
        rules=[
            PermissionRule(
                decision=RuleDecision.DENY,
                tool="shell",
                pattern="rm *",
                description="destructive shell",
            )
        ],
        allowed_tools=["read_file", "list_dir"],
        denied_tools=["shell", "write_file"],
    )


@pytest.fixture
def permission_app(monkeypatch: pytest.MonkeyPatch, admin_config: PermissionConfig) -> FastAPI:
    """A minimal app serving the permissions router behind the auth middleware."""
    monkeypatch.setattr(permissions_module, "get_engine", lambda: StubEngine(admin_config))
    app = FastAPI()
    app.add_middleware(AuthMiddleware, public_endpoints=set())
    app.include_router(permissions_router, prefix="/api/v1/permissions")
    return app


@pytest.fixture
def client(permission_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(permission_app) as test_client:
        yield test_client


@pytest.fixture
def auth_enabled() -> Iterator[None]:
    original = settings.enable_auth
    settings.enable_auth = True
    try:
        yield
    finally:
        settings.enable_auth = original


def _bearer(scopes: list[str]) -> dict[str, str]:
    token = create_access_token("test-user", scopes)
    return {"Authorization": f"Bearer {token}"}


def test_config_path_is_not_a_public_endpoint() -> None:
    """The read path is a protected endpoint, not an intentionally public one."""
    assert CONFIG_PATH not in settings.auth_public_endpoints
    assert not CONFIG_PATH.startswith(("/static/", "/assets/", "/docs", "/openapi"))


def test_get_config_rejects_anonymous_request(client: TestClient, auth_enabled: None) -> None:
    response = client.get(CONFIG_PATH)

    assert response.status_code == 401


def test_get_config_rejects_authenticated_non_admin(client: TestClient, auth_enabled: None) -> None:
    response = client.get(CONFIG_PATH, headers=_bearer(["read", "write"]))

    assert response.status_code == 403
    assert "allowed_tools" not in response.text
    assert "denied_tools" not in response.text


def test_get_config_returns_policy_for_admin(client: TestClient, auth_enabled: None) -> None:
    response = client.get(CONFIG_PATH, headers=_bearer(["admin"]))

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == PermissionMode.STRICT.value
    assert body["tier"] == PermissionTier.FULL_WRITE.value
    assert body["allowed_tools"] == ["read_file", "list_dir"]
    assert body["denied_tools"] == ["shell", "write_file"]
    assert body["rules"] == [
        {
            "decision": RuleDecision.DENY.value,
            "tool": "shell",
            "pattern": "rm *",
            "description": "destructive shell",
        }
    ]


def test_put_config_rejects_anonymous_request(client: TestClient, auth_enabled: None) -> None:
    response = client.put(CONFIG_PATH, json={"mode": PermissionMode.PLAN.value})

    assert response.status_code == 401


def test_get_and_put_config_reject_the_same_callers(
    client: TestClient,
    auth_enabled: None,
) -> None:
    """Read and write share one gate, so the read path grants no extra access."""
    for scopes, expected in ((None, 401), (["read", "write"], 403), (["admin"], 200)):
        headers = {} if scopes is None else _bearer(scopes)
        read_status = client.get(CONFIG_PATH, headers=headers).status_code
        write_status = client.put(CONFIG_PATH, json={"mode": PermissionMode.PLAN.value}, headers=headers).status_code

        assert read_status == expected
        assert write_status == expected


def test_get_config_stays_readable_in_local_mode(client: TestClient) -> None:
    """With authentication disabled the seeded local identity resolves to admin."""
    assert settings.enable_auth is False

    response = client.get(CONFIG_PATH)

    assert response.status_code == 200
    assert response.json()["mode"] == PermissionMode.STRICT.value

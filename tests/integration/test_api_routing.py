import pytest

from app.api.v1 import permissions
from app.core.permission_rules import PermissionConfig


@pytest.mark.asyncio
async def test_nested_api_routes_are_reachable(client) -> None:
    health_response = await client.get("/api/v1/health")
    auth_health_response = await client.get("/api/v1/auth/health")

    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}
    assert auth_health_response.status_code == 200
    assert auth_health_response.json()["authentication_enabled"] is False


@pytest.mark.asyncio
async def test_permission_config_route_uses_admin_dependency(client, monkeypatch) -> None:
    class FakeEngine:
        def __init__(self) -> None:
            self.config = PermissionConfig()

        def get_permission_config(self) -> PermissionConfig:
            return self.config

        def update_permission_config(self, config: PermissionConfig) -> None:
            self.config = config

    monkeypatch.setattr(permissions, "get_engine", lambda: FakeEngine())
    response = await client.put("/api/v1/permissions/config", json={"mode": "default"})

    assert response.status_code == 200
    assert response.json()["status"] == "updated"

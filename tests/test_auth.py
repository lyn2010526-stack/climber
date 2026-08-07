"""Authentication middleware tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.middleware.auth import create_jwt_token, get_user_store


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
class TestAuthDisabled:
    """When ENABLE_AUTH is false (default), all endpoints are accessible."""

    async def test_health_accessible_without_auth(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200

    async def test_api_accessible_without_auth(self, client):
        resp = await client.get("/api/v1/sessions")
        assert resp.status_code in (200, 404)

    async def test_docs_accessible_without_auth(self, client):
        resp = await client.get("/docs")
        assert resp.status_code in (200, 307, 404)


@pytest.mark.anyio
class TestAuthEnabled:
    """When ENABLE_AUTH is true, protected endpoints require authentication."""

    @pytest.fixture(autouse=True)
    def enable_auth(self):
        with patch("app.middleware.auth.settings") as mock_settings, \
             patch("app.config.settings") as mock_config:
            mock_settings.enable_auth = True
            mock_settings.auth_public_endpoints = {
                "/health", "/health/logs", "/metrics", "/docs", "/openapi.json", "/favicon.ico", "/"
            }
            mock_settings.app_secret_key = "test-secret-key-for-testing-only"
            mock_settings.jwt_algorithm = "HS256"
            mock_settings.jwt_expire_minutes = 1440
            mock_config.enable_auth = True
            mock_config.auth_public_endpoints = [
                "/health", "/health/logs", "/metrics", "/docs", "/openapi.json", "/favicon.ico", "/"
            ]
            mock_config.app_secret_key = "test-secret-key-for-testing-only"
            mock_config.jwt_algorithm = "HS256"
            mock_config.jwt_expire_minutes = 1440
            yield

    async def test_public_endpoint_still_accessible(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200

    async def test_protected_endpoint_rejects_anonymous(self, client):
        resp = await client.get("/api/v1/sessions")
        assert resp.status_code == 401
        data = resp.json()
        assert data["type"] == "authentication_required"
        assert "X-API-Key" in data["hint"]

    async def test_api_key_auth_success(self, client):
        store = get_user_store()
        raw_key, key_id = store.create_key(owner="test-user", scopes=["read", "write"])
        try:
            resp = await client.get("/api/v1/sessions", headers={"X-API-Key": raw_key})
            assert resp.status_code in (200, 404)
        finally:
            store.revoke_key(key_id)

    async def test_api_key_auth_invalid_key(self, client):
        resp = await client.get("/api/v1/sessions", headers={"X-API-Key": "invalid-key"})
        assert resp.status_code == 401

    async def test_jwt_auth_success(self, client):
        token = create_jwt_token(subject="test-user", scopes=["read", "write"])
        resp = await client.get(
            "/api/v1/sessions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code in (200, 404)

    async def test_jwt_auth_invalid_token(self, client):
        resp = await client.get(
            "/api/v1/sessions",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert resp.status_code == 401


class TestUserStore:
    """Test the in-memory user/API key store."""

    def test_create_key_returns_raw_and_id(self):
        store = get_user_store()
        raw_key, key_id = store.create_key(owner="user1")
        assert raw_key.startswith("ae_")
        assert key_id.startswith("kid_")
        store.revoke_key(key_id)

    def test_validate_key_success(self):
        store = get_user_store()
        raw_key, key_id = store.create_key(owner="user1", scopes=["read"])
        entry = store.validate_key(raw_key)
        assert entry is not None
        assert entry.owner == "user1"
        assert "read" in entry.scopes
        store.revoke_key(key_id)

    def test_validate_key_invalid(self):
        store = get_user_store()
        entry = store.validate_key("non-existent-key")
        assert entry is None

    def test_revoke_key(self):
        store = get_user_store()
        raw_key, key_id = store.create_key(owner="user1")
        assert store.validate_key(raw_key) is not None
        assert store.revoke_key(key_id) is True
        assert store.validate_key(raw_key) is None

    def test_key_hash_not_stored_in_plain_text(self):
        store = get_user_store()
        raw_key, key_id = store.create_key(owner="user1")
        entry = store.validate_key(raw_key)
        assert entry is not None
        assert entry.key_hash != raw_key
        store.revoke_key(key_id)


class TestJwtToken:
    """Test JWT token creation and verification."""

    @pytest.fixture(autouse=True)
    def setup_secret(self):
        with patch("app.middleware.auth.settings") as mock_settings, \
             patch("app.config.settings") as mock_config:
            mock_settings.app_secret_key = "test-secret-key-for-testing-only"
            mock_settings.jwt_algorithm = "HS256"
            mock_settings.jwt_expire_minutes = 1440
            mock_config.app_secret_key = "test-secret-key-for-testing-only"
            mock_config.jwt_algorithm = "HS256"
            mock_config.jwt_expire_minutes = 1440
            yield

    def test_create_token_returns_string(self):
        token = create_jwt_token(subject="user1")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_contains_subject(self):
        import jwt as pyjwt
        token = create_jwt_token(subject="user1", scopes=["admin"])
        payload = pyjwt.decode(token, "test-secret-key-for-testing-only", algorithms=["HS256"])
        assert payload["sub"] == "user1"
        assert "admin" in payload["scopes"]

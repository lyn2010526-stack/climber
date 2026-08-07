"""Tests for mongodb integration."""


import pytest

from app.integrations.mongodb_integration import (
    MongoDBAuthType,
    MongoDBClient,
    MongoDBConfig,
    MongoDBRateLimiter,
    MongoDBResponse,
    MongoDBRetryPolicy,
    MongoDBWebhookHandler,
)


@pytest.fixture
def config() -> MongoDBConfig:
    return MongoDBConfig(
        base_url="https://api.example.com",
        api_key="test-key",
        api_secret="test-secret",
        auth_type="api_key",
        timeout=10.0,
    )


@pytest.fixture
def client(config: MongoDBConfig) -> MongoDBClient:
    return MongoDBClient(config)


class TestMongoDBConfig:
    """Tests for configuration."""

    def test_default_config(self):
        config = MongoDBConfig()
        assert config.timeout == 30.0
        assert config.auth_type == "api_key"

    def test_custom_config(self, config):
        assert config.base_url == "https://api.example.com"
        assert config.api_key == "test-key"


class TestMongoDBRetryPolicy:
    """Tests for retry policy."""

    def test_default_policy(self):
        policy = MongoDBRetryPolicy()
        assert policy.max_retries == 3
        assert policy.initial_delay == 1.0

    def test_exponential_delay(self):
        policy = MongoDBRetryPolicy(initial_delay=1.0, exponential_base=2.0)
        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 4.0

    def test_max_delay_cap(self):
        policy = MongoDBRetryPolicy(initial_delay=1.0, max_delay=5.0)
        assert policy.get_delay(10) == 5.0


class TestMongoDBClient:
    """Tests for integration client."""

    @pytest.mark.asyncio
    async def test_build_headers_api_key(self, client):
        headers = client._build_headers()
        assert "X-API-Key" in headers
        assert headers["X-API-Key"] == "test-key"

    @pytest.mark.asyncio
    async def test_build_headers_bearer(self, config):
        config.auth_type = "bearer"
        client = MongoDBClient(config)
        headers = client._build_headers()
        assert headers["Authorization"] == "Bearer test-key"

    @pytest.mark.asyncio
    async def test_build_headers_extra(self, client):
        headers = client._build_headers({"X-Custom": "value"})
        assert headers["X-Custom"] == "value"


class TestMongoDBResponse:
    """Tests for response wrapper."""

    def test_success_response(self):
        resp = MongoDBResponse(status_code=200, headers={}, body={"ok": True}, duration_ms=100)
        assert resp.is_success is True
        assert resp.is_rate_limited is False

    def test_rate_limited_response(self):
        resp = MongoDBResponse(status_code=429, headers={}, body={}, duration_ms=0)
        assert resp.is_rate_limited is True
        assert resp.is_success is False


class TestMongoDBWebhookHandler:
    """Tests for webhook handler."""

    @pytest.mark.asyncio
    async def test_handle_known_event(self):
        handler = MongoDBWebhookHandler("secret")
        called_with = {}

        async def mock_handler(payload):
            called_with.update(payload)
            return {"processed": True}

        handler.register_handler("test.event", mock_handler)
        result = await handler.handle({"type": "test.event", "data": "value"})
        assert result["status"] == "handled"
        assert called_with["data"] == "value"

    @pytest.mark.asyncio
    async def test_handle_unknown_event(self):
        handler = MongoDBWebhookHandler("secret")
        result = await handler.handle({"type": "unknown"})
        assert result["status"] == "ignored"


class TestMongoDBRateLimiter:
    """Tests for rate limiter."""

    @pytest.mark.asyncio
    async def test_acquire_within_burst(self):
        limiter = MongoDBRateLimiter(rate=10, burst=5)
        wait = await limiter.acquire()
        assert wait == 0

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        limiter = MongoDBRateLimiter(rate=1, burst=1)
        await limiter.acquire()
        wait = await limiter.acquire()
        assert wait > 0


class TestMongoDBAuthType:
    """Tests for auth type enum."""

    def test_auth_types(self):
        assert MongoDBAuthType.API_KEY.value == "api_key"
        assert MongoDBAuthType.BEARER.value == "bearer"
        assert MongoDBAuthType.OAUTH2.value == "oauth2"

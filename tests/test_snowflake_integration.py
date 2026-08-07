"""Tests for snowflake integration."""


import pytest

from app.integrations.snowflake_integration import (
    SnowflakeAuthType,
    SnowflakeClient,
    SnowflakeConfig,
    SnowflakeRateLimiter,
    SnowflakeResponse,
    SnowflakeRetryPolicy,
    SnowflakeWebhookHandler,
)


@pytest.fixture
def config() -> SnowflakeConfig:
    return SnowflakeConfig(
        base_url="https://api.example.com",
        api_key="test-key",
        api_secret="test-secret",
        auth_type="api_key",
        timeout=10.0,
    )


@pytest.fixture
def client(config: SnowflakeConfig) -> SnowflakeClient:
    return SnowflakeClient(config)


class TestSnowflakeConfig:
    """Tests for configuration."""

    def test_default_config(self):
        config = SnowflakeConfig()
        assert config.timeout == 30.0
        assert config.auth_type == "api_key"

    def test_custom_config(self, config):
        assert config.base_url == "https://api.example.com"
        assert config.api_key == "test-key"


class TestSnowflakeRetryPolicy:
    """Tests for retry policy."""

    def test_default_policy(self):
        policy = SnowflakeRetryPolicy()
        assert policy.max_retries == 3
        assert policy.initial_delay == 1.0

    def test_exponential_delay(self):
        policy = SnowflakeRetryPolicy(initial_delay=1.0, exponential_base=2.0)
        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 4.0

    def test_max_delay_cap(self):
        policy = SnowflakeRetryPolicy(initial_delay=1.0, max_delay=5.0)
        assert policy.get_delay(10) == 5.0


class TestSnowflakeClient:
    """Tests for integration client."""

    @pytest.mark.asyncio
    async def test_build_headers_api_key(self, client):
        headers = client._build_headers()
        assert "X-API-Key" in headers
        assert headers["X-API-Key"] == "test-key"

    @pytest.mark.asyncio
    async def test_build_headers_bearer(self, config):
        config.auth_type = "bearer"
        client = SnowflakeClient(config)
        headers = client._build_headers()
        assert headers["Authorization"] == "Bearer test-key"

    @pytest.mark.asyncio
    async def test_build_headers_extra(self, client):
        headers = client._build_headers({"X-Custom": "value"})
        assert headers["X-Custom"] == "value"


class TestSnowflakeResponse:
    """Tests for response wrapper."""

    def test_success_response(self):
        resp = SnowflakeResponse(status_code=200, headers={}, body={"ok": True}, duration_ms=100)
        assert resp.is_success is True
        assert resp.is_rate_limited is False

    def test_rate_limited_response(self):
        resp = SnowflakeResponse(status_code=429, headers={}, body={}, duration_ms=0)
        assert resp.is_rate_limited is True
        assert resp.is_success is False


class TestSnowflakeWebhookHandler:
    """Tests for webhook handler."""

    @pytest.mark.asyncio
    async def test_handle_known_event(self):
        handler = SnowflakeWebhookHandler("secret")
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
        handler = SnowflakeWebhookHandler("secret")
        result = await handler.handle({"type": "unknown"})
        assert result["status"] == "ignored"


class TestSnowflakeRateLimiter:
    """Tests for rate limiter."""

    @pytest.mark.asyncio
    async def test_acquire_within_burst(self):
        limiter = SnowflakeRateLimiter(rate=10, burst=5)
        wait = await limiter.acquire()
        assert wait == 0

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        limiter = SnowflakeRateLimiter(rate=1, burst=1)
        await limiter.acquire()
        wait = await limiter.acquire()
        assert wait > 0


class TestSnowflakeAuthType:
    """Tests for auth type enum."""

    def test_auth_types(self):
        assert SnowflakeAuthType.API_KEY.value == "api_key"
        assert SnowflakeAuthType.BEARER.value == "bearer"
        assert SnowflakeAuthType.OAUTH2.value == "oauth2"

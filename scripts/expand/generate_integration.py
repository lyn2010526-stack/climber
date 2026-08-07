#!/usr/bin/env python3
"""Generate integration modules and test suites."""

from __future__ import annotations

from pathlib import Path

BASE = Path("/workspace/agent-engine")


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def gen_integration(name: str, class_name: str) -> str:
    return f'''"""Integration module: {name} - External service connector."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta
from typing import Any, Optional, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum

import httpx
import structlog

logger = structlog.get_logger()


class {class_name}AuthType(str, Enum):
    """Authentication types."""
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    BASIC = "basic"
    BEARER = "bearer"
    HMAC = "hmac"
    NONE = "none"


class {class_name}RetryPolicy:
    """Retry policy configuration."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        retry_on_status: list[int] | None = None,
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retry_on_status = retry_on_status or [429, 500, 502, 503, 504]

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        delay = self.initial_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)


@dataclass
class {class_name}Config:
    """Configuration for {name} integration."""
    base_url: str = ""
    api_key: str = ""
    api_secret: str = ""
    auth_type: str = "api_key"
    timeout: float = 30.0
    max_connections: int = 100
    max_keepalive: int = 20
    pool_timeout: float = 5.0
    verify_ssl: bool = True
    default_headers: dict[str, str] = field(default_factory=dict)
    webhook_secret: str = ""
    rate_limit_per_second: float = 10.0
    retry_policy: {class_name}RetryPolicy = field(default_factory={class_name}RetryPolicy)


@dataclass
class {class_name}Response:
    """Standardized response from {name}."""
    status_code: int
    headers: dict[str, str]
    body: Any
    duration_ms: float
    cached: bool = False
    retry_count: int = 0

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def is_rate_limited(self) -> bool:
        return self.status_code == 429


class {class_name}Client:
    """Client for {name} integration."""

    def __init__(self, config: {class_name}Config):
        self.config = config
        self._client: httpx.AsyncClient | None = None
        self._rate_limit_tokens: float = config.rate_limit_per_second
        self._rate_limit_last_refill: float = time.monotonic()
        self._cache: dict[str, tuple[Any, float]] = {{}}

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            limits = httpx.Limits(
                max_connections=self.config.max_connections,
                max_keepalive_connections=self.config.max_keepalive,
            )
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                verify=self.config.verify_ssl,
                limits=limits,
            )
        return self._client

    def _build_headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """Build request headers."""
        headers = dict(self.config.default_headers)
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"
        headers["User-Agent"] = "AgentEngine/1.0"

        if self.config.auth_type == "api_key" and self.config.api_key:
            headers["X-API-Key"] = self.config.api_key
        elif self.config.auth_type == "bearer" and self.config.api_key:
            headers["Authorization"] = f"Bearer {{self.config.api_key}}"

        if extra:
            headers.update(extra)
        return headers

    async def _acquire_rate_limit(self) -> None:
        """Acquire rate limit token."""
        now = time.monotonic()
        elapsed = now - self._rate_limit_last_refill
        self._rate_limit_tokens = min(
            self.config.rate_limit_per_second,
            self._rate_limit_tokens + elapsed * self.config.rate_limit_per_second,
        )
        self._rate_limit_last_refill = now

        if self._rate_limit_tokens < 1:
            wait = (1 - self._rate_limit_tokens) / self.config.rate_limit_per_second
            await asyncio.sleep(wait)
            self._rate_limit_tokens = 0
        else:
            self._rate_limit_tokens -= 1

    async def request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        body: Any = None,
        headers: dict | None = None,
        use_cache: bool = False,
        cache_ttl: int = 300,
    ) -> {class_name}Response:
        """Make HTTP request with retry and caching."""
        cache_key = f"{{method}}:{{path}}:{{hash(str(params))}}"
        if use_cache and method == "GET" and cache_key in self._cache:
            cached_data, expires = self._cache[cache_key]
            if time.time() < expires:
                return {class_name}Response(status_code=200, headers={{}}, body=cached_data, duration_ms=0, cached=True)

        await self._acquire_rate_limit()
        client = await self._get_client()
        request_headers = self._build_headers(headers)

        retry_policy = self.config.retry_policy
        last_error = None

        for attempt in range(retry_policy.max_retries + 1):
            start = time.time()
            try:
                response = await client.request(
                    method, path, params=params, json=body, headers=request_headers
                )
                duration = (time.time() - start) * 1000

                if response.status_code in retry_policy.retry_on_status and attempt < retry_policy.max_retries:
                    delay = retry_policy.get_delay(attempt)
                    await asyncio.sleep(delay)
                    continue

                result = {class_name}Response(
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    body=response.json() if response.content else None,
                    duration_ms=duration,
                    retry_count=attempt,
                )

                if use_cache and method == "GET" and result.is_success:
                    self._cache[cache_key] = (result.body, time.time() + cache_ttl)

                return result
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = e
                if attempt < retry_policy.max_retries:
                    delay = retry_policy.get_delay(attempt)
                    await asyncio.sleep(delay)

        return {class_name}Response(status_code=0, headers={{}}, body=str(last_error), duration_ms=0)

    async def get(self, path: str, **kwargs) -> {class_name}Response:
        """Make GET request."""
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> {class_name}Response:
        """Make POST request."""
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs) -> {class_name}Response:
        """Make PUT request."""
        return await self.request("PUT", path, **kwargs)

    async def delete(self, path: str, **kwargs) -> {class_name}Response:
        """Make DELETE request."""
        return await self.request("DELETE", path, **kwargs)

    async def stream(self, path: str, **kwargs) -> AsyncIterator[bytes]:
        """Stream response."""
        client = await self._get_client()
        async with client.stream("GET", path, headers=self._build_headers()) as response:
            async for chunk in response.aiter_bytes():
                yield chunk

    async def close(self) -> None:
        """Close client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature."""
        expected = hmac.new(
            self.config.webhook_secret.encode(), payload, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)


class {class_name}WebhookHandler:
    """Handle incoming webhooks from {name}."""

    def __init__(self, secret: str):
        self.secret = secret
        self._handlers: dict[str, callable] = {{}}

    def register_handler(self, event_type: str, handler: callable) -> None:
        """Register event handler."""
        self._handlers[event_type] = handler

    async def handle(self, payload: dict, signature: str | None = None) -> dict:
        """Process webhook payload."""
        if signature and not await self._verify_signature(payload, signature):
            return {{"error": "Invalid signature"}}

        event_type = payload.get("type", "unknown")
        handler = self._handlers.get(event_type)
        if handler:
            result = await handler(payload)
            return {{"status": "handled", "result": result}}
        return {{"status": "ignored", "event": event_type}}

    async def _verify_signature(self, payload: dict, signature: str) -> bool:
        """Verify webhook signature."""
        payload_bytes = json.dumps(payload, sort_keys=True).encode()
        expected = hmac.new(self.secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


class {class_name}RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, rate: float, burst: int = 1):
        self.rate = rate
        self.burst = burst
        self._tokens = float(burst)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> float:
        """Acquire a token, returns wait time."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
            self._last_refill = now

            if self._tokens >= 1:
                self._tokens -= 1
                return 0
            wait = (1 - self._tokens) / self.rate
            return wait

    async def wait(self) -> None:
        """Wait until a token is available."""
        wait_time = await self.acquire()
        if wait_time > 0:
            await asyncio.sleep(wait_time)
'''


def gen_integration_test(name: str, class_name: str) -> str:
    return f'''"""Tests for {name} integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.integrations.{name}_integration import (
    {class_name}Client,
    {class_name}Config,
    {class_name}Response,
    {class_name}RetryPolicy,
    {class_name}WebhookHandler,
    {class_name}RateLimiter,
    {class_name}AuthType,
)


@pytest.fixture
def config() -> {class_name}Config:
    return {class_name}Config(
        base_url="https://api.example.com",
        api_key="test-key",
        api_secret="test-secret",
        auth_type="api_key",
        timeout=10.0,
    )


@pytest.fixture
def client(config: {class_name}Config) -> {class_name}Client:
    return {class_name}Client(config)


class Test{class_name}Config:
    """Tests for configuration."""

    def test_default_config(self):
        config = {class_name}Config()
        assert config.timeout == 30.0
        assert config.auth_type == "api_key"

    def test_custom_config(self, config):
        assert config.base_url == "https://api.example.com"
        assert config.api_key == "test-key"


class Test{class_name}RetryPolicy:
    """Tests for retry policy."""

    def test_default_policy(self):
        policy = {class_name}RetryPolicy()
        assert policy.max_retries == 3
        assert policy.initial_delay == 1.0

    def test_exponential_delay(self):
        policy = {class_name}RetryPolicy(initial_delay=1.0, exponential_base=2.0)
        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 4.0

    def test_max_delay_cap(self):
        policy = {class_name}RetryPolicy(initial_delay=1.0, max_delay=5.0)
        assert policy.get_delay(10) == 5.0


class Test{class_name}Client:
    """Tests for integration client."""

    @pytest.mark.asyncio
    async def test_build_headers_api_key(self, client):
        headers = client._build_headers()
        assert "X-API-Key" in headers
        assert headers["X-API-Key"] == "test-key"

    @pytest.mark.asyncio
    async def test_build_headers_bearer(self, config):
        config.auth_type = "bearer"
        client = {class_name}Client(config)
        headers = client._build_headers()
        assert headers["Authorization"] == "Bearer test-key"

    @pytest.mark.asyncio
    async def test_build_headers_extra(self, client):
        headers = client._build_headers({{"X-Custom": "value"}})
        assert headers["X-Custom"] == "value"


class Test{class_name}Response:
    """Tests for response wrapper."""

    def test_success_response(self):
        resp = {class_name}Response(status_code=200, headers={{}}, body={{"ok": True}}, duration_ms=100)
        assert resp.is_success is True
        assert resp.is_rate_limited is False

    def test_rate_limited_response(self):
        resp = {class_name}Response(status_code=429, headers={{}}, body={{}}, duration_ms=0)
        assert resp.is_rate_limited is True
        assert resp.is_success is False


class Test{class_name}WebhookHandler:
    """Tests for webhook handler."""

    @pytest.mark.asyncio
    async def test_handle_known_event(self):
        handler = {class_name}WebhookHandler("secret")
        called_with = {{}}

        async def mock_handler(payload):
            called_with.update(payload)
            return {{"processed": True}}

        handler.register_handler("test.event", mock_handler)
        result = await handler.handle({{"type": "test.event", "data": "value"}})
        assert result["status"] == "handled"
        assert called_with["data"] == "value"

    @pytest.mark.asyncio
    async def test_handle_unknown_event(self):
        handler = {class_name}WebhookHandler("secret")
        result = await handler.handle({{"type": "unknown"}})
        assert result["status"] == "ignored"


class Test{class_name}RateLimiter:
    """Tests for rate limiter."""

    @pytest.mark.asyncio
    async def test_acquire_within_burst(self):
        limiter = {class_name}RateLimiter(rate=10, burst=5)
        wait = await limiter.acquire()
        assert wait == 0

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        limiter = {class_name}RateLimiter(rate=1, burst=1)
        await limiter.acquire()
        wait = await limiter.acquire()
        assert wait > 0


class Test{class_name}AuthType:
    """Tests for auth type enum."""

    def test_auth_types(self):
        assert {class_name}AuthType.API_KEY.value == "api_key"
        assert {class_name}AuthType.BEARER.value == "bearer"
        assert {class_name}AuthType.OAUTH2.value == "oauth2"
'''


def main() -> None:
    all_files: dict[str, str] = {}

    integrations = [
        ("slack", "Slack", "Slack workspace integration"),
        ("github", "GitHub", "GitHub repository integration"),
        ("jira", "Jira", "Jira project management"),
        ("notion", "Notion", "Notion workspace integration"),
        ("stripe", "Stripe", "Stripe payment processing"),
        ("sendgrid", "SendGrid", "SendGrid email delivery"),
        ("twilio", "Twilio", "Twilio SMS and voice"),
        ("aws_s3", "AwsS3", "AWS S3 storage"),
        ("gcp_storage", "GcpStorage", "Google Cloud Storage"),
        ("azure_blob", "AzureBlob", "Azure Blob Storage"),
        ("datadog", "Datadog", "Datadog monitoring"),
        ("pagerduty", "PagerDuty", "PagerDuty incident management"),
        ("opsgenie", "Opsgenie", "Opsgenie alerting"),
        ("grafana", "Grafana", "Grafana dashboards"),
        ("elasticsearch", "Elasticsearch", "Elasticsearch search engine"),
        ("redis_cloud", "RedisCloud", "Redis Cloud cache"),
        ("postgres", "Postgres", "PostgreSQL database"),
        ("mongodb", "MongoDB", "MongoDB document store"),
        ("snowflake", "Snowflake", "Snowflake data warehouse"),
        ("bigquery", "BigQuery", "Google BigQuery"),
    ]

    print(f"Generating {len(integrations)} integration modules with tests...")

    for name, class_name, _desc in integrations:
        integration_content = gen_integration(name, class_name)
        all_files[f"app/integrations/{name}_integration.py"] = integration_content

        test_content = gen_integration_test(name, class_name)
        all_files[f"tests/test_{name}_integration.py"] = test_content

    print(f"Writing {len(all_files)} files...")
    for path_str, content in all_files.items():
        write_file(BASE / path_str, content)

    print(f"Done! Generated {len(all_files)} files across {len(integrations)} integrations.")


if __name__ == "__main__":
    main()

"""Integration module: elasticsearch - External service connector."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


class ElasticsearchAuthType(StrEnum):
    """Authentication types."""
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    BASIC = "basic"
    BEARER = "bearer"
    HMAC = "hmac"
    NONE = "none"


class ElasticsearchRetryPolicy:
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
class ElasticsearchConfig:
    """Configuration for elasticsearch integration."""
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
    retry_policy: ElasticsearchRetryPolicy = field(default_factory=ElasticsearchRetryPolicy)


@dataclass
class ElasticsearchResponse:
    """Standardized response from elasticsearch."""
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


class ElasticsearchClient:
    """Client for elasticsearch integration."""

    def __init__(self, config: ElasticsearchConfig):
        self.config = config
        self._client: httpx.AsyncClient | None = None
        self._rate_limit_tokens: float = config.rate_limit_per_second
        self._rate_limit_last_refill: float = time.monotonic()
        self._cache: dict[str, tuple[Any, float]] = {}

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
            headers["Authorization"] = f"Bearer {self.config.api_key}"

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
    ) -> ElasticsearchResponse:
        """Make HTTP request with retry and caching."""
        cache_key = f"{method}:{path}:{hash(str(params))}"
        if use_cache and method == "GET" and cache_key in self._cache:
            cached_data, expires = self._cache[cache_key]
            if time.time() < expires:
                return ElasticsearchResponse(status_code=200, headers={}, body=cached_data, duration_ms=0, cached=True)

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

                result = ElasticsearchResponse(
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

        return ElasticsearchResponse(status_code=0, headers={}, body=str(last_error), duration_ms=0)

    async def get(self, path: str, **kwargs) -> ElasticsearchResponse:
        """Make GET request."""
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> ElasticsearchResponse:
        """Make POST request."""
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs) -> ElasticsearchResponse:
        """Make PUT request."""
        return await self.request("PUT", path, **kwargs)

    async def delete(self, path: str, **kwargs) -> ElasticsearchResponse:
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


class ElasticsearchWebhookHandler:
    """Handle incoming webhooks from elasticsearch."""

    def __init__(self, secret: str):
        self.secret = secret
        self._handlers: dict[str, callable] = {}

    def register_handler(self, event_type: str, handler: callable) -> None:
        """Register event handler."""
        self._handlers[event_type] = handler

    async def handle(self, payload: dict, signature: str | None = None) -> dict:
        """Process webhook payload."""
        if signature and not await self._verify_signature(payload, signature):
            return {"error": "Invalid signature"}

        event_type = payload.get("type", "unknown")
        handler = self._handlers.get(event_type)
        if handler:
            result = await handler(payload)
            return {"status": "handled", "result": result}
        return {"status": "ignored", "event": event_type}

    async def _verify_signature(self, payload: dict, signature: str) -> bool:
        """Verify webhook signature."""
        payload_bytes = json.dumps(payload, sort_keys=True).encode()
        expected = hmac.new(self.secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


class ElasticsearchRateLimiter:
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

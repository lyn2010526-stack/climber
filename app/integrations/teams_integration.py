"""Integration: teams - Third-party integration."""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


class TeamsAuthType(StrEnum):
    """Authentication type."""
    API_KEY = 'api_key'
    OAUTH2 = 'oauth2'
    BASIC = 'basic'
    BEARER = 'bearer'
    HMAC = 'hmac'


class TeamsRateLimitStrategy(StrEnum):
    """Rate limit strategy."""
    FIXED_WINDOW = 'fixed_window'
    SLIDING_WINDOW = 'sliding_window'
    TOKEN_BUCKET = 'token_bucket'
    LEAKY_BUCKET = 'leaky_bucket'


@dataclass
class TeamsCredentials:
    """Integration credentials."""
    api_key: str = ''
    api_secret: str = ''
    access_token: str = ''
    refresh_token: str = ''
    token_expiry: datetime | None = None
    auth_type: str = 'api_key'


@dataclass
class TeamsConfig:
    """Integration configuration."""
    base_url: str = ''
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit_per_second: int = 10
    enable_caching: bool = True
    cache_ttl: int = 300
    verify_ssl: bool = True
    custom_headers: dict[str, str] = field(default_factory=dict)


@dataclass
class TeamsResponse:
    """API response wrapper."""
    success: bool = False
    status_code: int = 0
    data: Any = None
    error: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    latency_ms: float = 0.0


@dataclass
class TeamsWebhook:
    """Webhook configuration."""
    id: str = ''
    url: str = ''
    events: list[str] = field(default_factory=list)
    secret: str = ''
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


class TeamsIntegration:
    """Main integration class."""

    def __init__(self, config: TeamsConfig | None = None, credentials: TeamsCredentials | None = None):
        self.config = config or TeamsConfig()
        self.credentials = credentials or TeamsCredentials()
        self._client: httpx.AsyncClient | None = None
        self._cache: dict[str, Any] = {}
        self._webhooks: dict[str, TeamsWebhook] = {}
        self._request_count = 0
        self._error_count = 0

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            headers = {'User-Agent': 'AgentEngine/1.0'}
            if self.credentials.api_key:
                headers['X-API-Key'] = self.credentials.api_key
            if self.credentials.access_token:
                headers['Authorization'] = f'Bearer {self.credentials.access_token}'
            headers.update(self.config.custom_headers)
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers=headers,
                timeout=self.config.timeout_seconds,
                verify=self.config.verify_ssl,
            )
        return self._client

    async def get(self, path: str, params: dict[str, Any] | None = None) -> TeamsResponse:
        """GET request."""
        return await self._request('GET', path, params=params)

    async def post(self, path: str, data: Any = None) -> TeamsResponse:
        """POST request."""
        return await self._request('POST', path, data=data)

    async def put(self, path: str, data: Any = None) -> TeamsResponse:
        """PUT request."""
        return await self._request('PUT', path, data=data)

    async def delete(self, path: str) -> TeamsResponse:
        """DELETE request."""
        return await self._request('DELETE', path)

    async def _request(
        self, method: str, path: str, params: dict[str, Any] | None = None, data: Any = None
    ) -> TeamsResponse:
        """Make HTTP request."""
        start = time.time()
        self._request_count += 1

        try:
            client = await self._get_client()
            response = await client.request(method, path, params=params, json=data)
            latency = (time.time() - start) * 1000

            return TeamsResponse(
                success=response.status_code < 400,
                status_code=response.status_code,
                data=response.json() if response.content else None,
                headers=dict(response.headers),
                latency_ms=latency,
            )
        except Exception as e:
            self._error_count += 1
            return TeamsResponse(
                success=False,
                error=str(e),
                latency_ms=(time.time() - start) * 1000,
            )

    def register_webhook(self, webhook: TeamsWebhook) -> None:
        """Register webhook."""
        self._webhooks[webhook.id] = webhook

    def verify_webhook_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """Verify webhook signature."""
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def close(self) -> None:
        """Close client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def get_stats(self) -> dict[str, Any]:
        """Get integration stats."""
        return {
            'total_requests': self._request_count,
            'total_errors': self._error_count,
            'error_rate': self._error_count / max(self._request_count, 1),
            'webhooks_count': len(self._webhooks),
        }

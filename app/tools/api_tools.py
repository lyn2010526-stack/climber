"""API integration tools - HTTP requests, rate limiting, retries."""

from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import httpx
import structlog

from app.tools import ToolRegistry

logger = structlog.get_logger()


class ApiTools:
                """HTTP API integration tools with rate limiting and retry logic."""

                def __init__(self):
                    self._rate_limiters: dict[str, list[float]] = {}
                    self._client: httpx.AsyncClient | None = None

                def register(self, registry: ToolRegistry) -> None:
                    """Register all API tools."""
                    registry.register(
                        name="api_http_request",
                        description="Make HTTP request with retries and rate limiting",
                        parameters={
                            "type": "object",
                            "properties": {
                                "url": {"type": "string"},
                                "method": {"type": "string"},
                                "headers": {"type": "object"},
                                "body": {"type": "object"},
                                "params": {"type": "object"},
                                "timeout": {"type": "number"},
                                "retries": {"type": "integer"},
                                "rate_limit": {"type": "number"},
                            },
                            "required": ["url"],
                        },
                        func=self.http_request,
                    )
                    registry.register(
                        name="api_oauth_token",
                        description="Obtain OAuth2 access token",
                        parameters={
                            "type": "object",
                            "properties": {
                                "token_url": {"type": "string"},
                                "client_id": {"type": "string"},
                                "client_secret": {"type": "string"},
                                "scope": {"type": "string"},
                                "grant_type": {"type": "string"},
                            },
                            "required": ["token_url", "client_id", "client_secret"],
                        },
                        func=self.get_oauth_token,
                    )
                    registry.register(
                        name="api_graphql_query",
                        description="Execute GraphQL query",
                        parameters={
                            "type": "object",
                            "properties": {
                                "endpoint": {"type": "string"},
                                "query": {"type": "string"},
                                "variables": {"type": "object"},
                                "headers": {"type": "object"},
                            },
                            "required": ["endpoint", "query"],
                        },
                        func=self.graphql_query,
                    )
                    registry.register(
                        name="api_paginate",
                        description="Fetch all pages from paginated API",
                        parameters={
                            "type": "object",
                            "properties": {
                                "url": {"type": "string"},
                                "page_param": {"type": "string"},
                                "page_size_param": {"type": "string"},
                                "page_size": {"type": "integer"},
                                "max_pages": {"type": "integer"},
                                "results_key": {"type": "string"},
                            },
                            "required": ["url"],
                        },
                        func=self.paginate,
                    )
                    registry.register(
                        name="api_rate_limit_check",
                        description="Check and enforce rate limits",
                        parameters={
                            "type": "object",
                            "properties": {
                                "key": {"type": "string"},
                                "max_requests": {"type": "integer"},
                                "window_seconds": {"type": "number"},
                            },
                            "required": ["key", "max_requests", "window_seconds"],
                        },
                        func=self.check_rate_limit,
                    )
                    registry.register(
                        name="api_cache_set",
                        description="Set a cached API response",
                        parameters={
                            "type": "object",
                            "properties": {
                                "key": {"type": "string"},
                                "value": {"type": "object"},
                                "ttl": {"type": "integer"},
                            },
                            "required": ["key", "value"],
                        },
                        func=self.cache_set,
                    )
                    registry.register(
                        name="api_cache_get",
                        description="Get cached API response",
                        parameters={
                            "type": "object",
                            "properties": {
                                "key": {"type": "string"},
                            },
                            "required": ["key"],
                        },
                        func=self.cache_get,
                    )

                def _check_rate_limit(self, domain: str, max_requests: int, window: float) -> bool:
                    """Check if request is within rate limit."""
                    now = time.time()
                    if domain not in self._rate_limiters:
                        self._rate_limiters[domain] = []

                    # Clean old entries
                    self._rate_limiters[domain] = [
                        t for t in self._rate_limiters[domain] if now - t < window
                    ]

                    if len(self._rate_limiters[domain]) >= max_requests:
                        return False

                    self._rate_limiters[domain].append(now)
                    return True

                def http_request(
                    self,
                    url: str,
                    method: str = "GET",
                    headers: dict | None = None,
                    body: dict | None = None,
                    params: dict | None = None,
                    timeout: float = 30.0,
                    retries: int = 3,
                    rate_limit: float | None = None,
                ) -> dict:
                    """Make HTTP request with retries."""
                    from app.utils.ssrf import blocked_reason

                    reason = blocked_reason(url)
                    if reason:
                        return {"error": f"Blocked URL: {reason}"}

                    domain = urlparse(url).netloc

                    if rate_limit:
                        max_req = int(rate_limit)
                        if not self._check_rate_limit(domain, max_req, 60.0):
                            return {"error": "Rate limit exceeded", "retry_after": 60.0}

                    last_error = None
                    for attempt in range(retries + 1):
                        try:
                            response = httpx.request(
                                method,
                                url,
                                headers=headers,
                                json=body,
                                params=params,
                                timeout=timeout,
                            )
                            return {
                                "status_code": response.status_code,
                                "headers": dict(response.headers),
                                "body": response.text[:10000],
                                "json": self._safe_json(response),
                                "attempt": attempt + 1,
                                "url": str(response.url),
                            }
                        except httpx.TimeoutException as e:
                            last_error = f"Timeout: {e}"
                        except httpx.HTTPError as e:
                            last_error = f"HTTP error: {e}"
                            if attempt < retries:
                                time.sleep(2 ** attempt)

                    return {"error": last_error, "attempts": retries + 1}

                def _safe_json(self, response: httpx.Response) -> Any:
                    """Safely parse JSON response."""
                    try:
                        return response.json()
                    except (json.JSONDecodeError, ValueError):
                        return None

                def get_oauth_token(
                    self, token_url: str, client_id: str, client_secret: str,
                    scope: str = "", grant_type: str = "client_credentials",
                ) -> dict:
                    """Obtain OAuth2 access token."""
                    data = {
                        "grant_type": grant_type,
                        "client_id": client_id,
                        "client_secret": client_secret,
                    }
                    if scope:
                        data["scope"] = scope

                    result = self.http_request(token_url, method="POST", body=data)
                    if result.get("status_code") == 200:
                        token_data = result.get("json", {})
                        return {
                            "access_token": token_data.get("access_token"),
                            "token_type": token_data.get("token_type", "Bearer"),
                            "expires_in": token_data.get("expires_in"),
                            "scope": token_data.get("scope"),
                        }
                    return {"error": "Token request failed", "details": result}

                def graphql_query(
                    self, endpoint: str, query: str, variables: dict | None = None,
                    headers: dict | None = None,
                ) -> dict:
                    """Execute GraphQL query."""
                    headers = headers or {}
                    headers.setdefault("Content-Type", "application/json")

                    payload = {"query": query}
                    if variables:
                        payload["variables"] = variables

                    return self.http_request(endpoint, method="POST", headers=headers, body=payload)

                def paginate(
                    self, url: str, page_param: str = "page", page_size_param: str = "per_page",
                    page_size: int = 50, max_pages: int = 100, results_key: str | None = None,
                ) -> dict:
                    """Fetch all pages from paginated API."""
                    all_results = []
                    page = 1

                    while page <= max_pages:
                        params = {page_param: page, page_size_param: page_size}
                        result = self.http_request(url, params=params)

                        if result.get("status_code") != 200:
                            break

                        data = result.get("json", {})
                        if results_key and isinstance(data, dict):
                            items = data.get(results_key, [])
                        elif isinstance(data, list):
                            items = data
                        else:
                            break

                        if not items:
                            break

                        all_results.extend(items)
                        page += 1

                        # Check if there are more pages
                        if len(items) < page_size:
                            break

                    return {
                        "results": all_results,
                        "total": len(all_results),
                        "pages_fetched": page - 1,
                    }

                def check_rate_limit(self, key: str, max_requests: int, window_seconds: float) -> dict:
                    """Check rate limit status."""
                    now = time.time()
                    if key not in self._rate_limiters:
                        self._rate_limiters[key] = []

                    # Clean old entries
                    self._rate_limiters[key] = [
                        t for t in self._rate_limiters[key] if now - t < window_seconds
                    ]

                    current = len(self._rate_limiters[key])
                    remaining = max(0, max_requests - current)
                    reset_time = self._rate_limiters[key][0] + window_seconds if self._rate_limiters[key] else now

                    return {
                        "key": key,
                        "current_requests": current,
                        "max_requests": max_requests,
                        "remaining": remaining,
                        "window_seconds": window_seconds,
                        "reset_at": datetime.fromtimestamp(reset_time).isoformat(),
                        "limited": remaining == 0,
                    }

                def cache_set(self, key: str, value: Any, ttl: int = 300) -> dict:
                    """Set cached value (in-memory)."""
                    if not hasattr(self, "_cache"):
                        self._cache: dict[str, tuple[Any, float]] = {}

                    self._cache[key] = (value, time.time() + ttl)
                    return {"key": key, "ttl": ttl, "cached": True}

                def cache_get(self, key: str) -> dict:
                    """Get cached value."""
                    if not hasattr(self, "_cache"):
                        return {"key": key, "found": False}

                    if key in self._cache:
                        value, expires = self._cache[key]
                        if time.time() < expires:
                            return {"key": key, "value": value, "found": True}
                        else:
                            del self._cache[key]

                    return {"key": key, "found": False}

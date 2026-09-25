"""Credential-only model discovery; independent of execution registries.

Provider contracts: platform.openai.com/docs/api-reference/models,
platform.claude.com/docs/en/api/models/list, ai.google.dev/api/models,
docs.ollama.com/api/tags. StepFun is queried at /v1/models following its
existing OpenAI-compatible adapter; unavailable discovery is reported
explicitly, never filled with aliases.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import socket
from typing import Any

import httpx

from app.utils.ssrf import _is_unsafe_ip

DISCOVERY_TIMEOUT = 12.0
MAX_PAGES = 10
MAX_MODELS = 2000
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
DEFAULT_BASES = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
    "google": "https://generativelanguage.googleapis.com/v1beta",
    "stepfun": "https://api.stepfun.com/v1",
    "ollama": None,
}


class DiscoveryError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 502):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class PublicModelTransport(httpx.AsyncHTTPTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        url = request.url
        if url.scheme != "https" or not url.host or url.userinfo:
            raise DiscoveryError("unsafe_endpoint", "Discovery requires a public HTTPS endpoint.", 422)
        try:
            addresses = await asyncio.get_running_loop().getaddrinfo(
                url.host, url.port or 443, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
            )
        except OSError:
            raise DiscoveryError("network_error", "Provider DNS resolution failed.") from None
        if not addresses:
            raise DiscoveryError("network_error", "Provider DNS resolution failed.")
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if not ip.is_global or _is_unsafe_ip(ip):
                raise DiscoveryError("unsafe_endpoint", "Discovery requires a public HTTPS endpoint.", 422)
        # Pin the validated address to close the DNS re-resolution window.
        # HTTPX documents sni_hostname for certificate verification against the original host.
        pinned = httpx.Request(
            request.method, url.copy_with(host=addresses[0][4][0]),
            headers=request.headers, stream=request.stream,
            extensions={**request.extensions, "sni_hostname": url.host},
        )
        return await super().handle_async_request(pinned)


async def discover_models(provider: str, api_key: str, base_url: str | None) -> dict[str, Any]:
    """Only caller-supplied, owner-checked credentials may enter this function."""
    if provider not in DEFAULT_BASES:
        raise DiscoveryError("unsupported_provider", "Provider is not supported by model discovery.", 400)
    if provider != "ollama" and not api_key.strip():
        raise DiscoveryError("missing_key", "Save a provider API key before discovery.", 400)
    base = (base_url or DEFAULT_BASES[provider] or "").strip().rstrip("/")
    if not base:
        raise DiscoveryError("missing_endpoint", "Save an explicit public HTTPS Ollama endpoint.", 400)
    try:
        parsed = httpx.URL(base)
    except (httpx.InvalidURL, ValueError):
        raise DiscoveryError("unsafe_endpoint", "Invalid provider endpoint.", 422) from None
    if parsed.scheme != "https" or not parsed.host or parsed.userinfo or parsed.query or parsed.fragment:
        raise DiscoveryError("unsafe_endpoint", "Use a public HTTPS base URL without credentials, query or fragment.", 422)

    path = "/api/tags" if provider == "ollama" else "/models"
    if provider == "anthropic":
        path = "/v1/models"
    headers = {"Accept": "application/json"}
    if provider == "google":
        headers["x-goog-api-key"] = api_key
    elif provider == "anthropic":
        headers.update({"x-api-key": api_key, "anthropic-version": "2023-06-01"})
    elif api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    params: dict[str, str | int] = {}
    if provider == "google":
        params["pageSize"] = 1000
    elif provider == "anthropic":
        params["limit"] = 1000
    models: dict[str, dict[str, str]] = {}
    cursors: set[str] = set()
    try:
        async with asyncio.timeout(DISCOVERY_TIMEOUT):
            async with httpx.AsyncClient(
                transport=PublicModelTransport(trust_env=False), trust_env=False, follow_redirects=False,
                timeout=httpx.Timeout(8.0, connect=3.0),
            ) as client:
                for _ in range(MAX_PAGES):
                    async with client.stream(
                        "GET", base + path, headers=headers, params=params,
                    ) as response:
                        if response.status_code in (401, 403):
                            raise DiscoveryError("provider_auth_failed", "Provider rejected the saved credential.", 424)
                        if response.status_code == 429:
                            raise DiscoveryError("rate_limited", "Provider rate limit reached; retry later.", 429)
                        if response.status_code in (404, 405, 501):
                            raise DiscoveryError("discovery_unavailable", "Provider endpoint does not support model discovery.", 424)
                        if response.is_redirect:
                            raise DiscoveryError("unsafe_redirect", "Provider redirects are disabled.", 422)
                        if response.status_code != 200:
                            raise DiscoveryError("provider_error", "Provider model discovery failed.")
                        body = bytearray()
                        async for chunk in response.aiter_bytes():
                            body.extend(chunk)
                            if len(body) > MAX_RESPONSE_BYTES:
                                raise DiscoveryError("response_too_large", "Provider response exceeded discovery limits.")
                    payload = json.loads(body)
                    field = "models" if provider in ("google", "ollama") else "data"
                    if not isinstance(payload, dict) or not isinstance(payload.get(field), list):
                        raise DiscoveryError("invalid_response", "Provider returned an invalid model list.")
                    for item in payload[field]:
                        if not isinstance(item, dict):
                            raise DiscoveryError("invalid_response", "Provider returned an invalid model entry.")
                        model_id = item.get("name" if provider in ("google", "ollama") else "id")
                        if not isinstance(model_id, str) or not model_id.strip() or len(model_id) > 512:
                            raise DiscoveryError("invalid_response", "Provider returned an invalid model identifier.")
                        if provider == "google":
                            methods = item.get("supportedGenerationMethods", [])
                            if not isinstance(methods, list):
                                raise DiscoveryError("invalid_response", "Provider returned invalid generation methods.")
                            if "generateContent" not in methods:
                                continue
                            model_id = model_id.removeprefix("models/")
                            if not model_id:
                                raise DiscoveryError("invalid_response", "Provider returned an invalid model identifier.")
                        label = item.get("display_name") or item.get("displayName") or model_id
                        models[model_id] = {
                            "provider": provider, "model_id": model_id,
                            "label": label if isinstance(label, str) and len(label) <= 512 else model_id,
                        }
                        if len(models) > MAX_MODELS:
                            raise DiscoveryError("response_too_large", "Provider response exceeded discovery limits.")
                    cursor = None
                    if provider == "google":
                        cursor = payload.get("nextPageToken")
                        cursor_param = "pageToken"
                    else:
                        cursor_param = "after_id" if provider == "anthropic" else "after"
                        has_more = payload.get("has_more", False)
                        if not isinstance(has_more, bool):
                            raise DiscoveryError("invalid_response", "Provider returned invalid pagination metadata.")
                        if has_more:
                            cursor = payload.get("last_id")
                            if not cursor:
                                raise DiscoveryError("invalid_response", "Provider omitted the pagination cursor.")
                    if cursor is not None and not isinstance(cursor, str):
                        raise DiscoveryError("invalid_response", "Provider returned an invalid pagination cursor.")
                    if not cursor:
                        return {
                            "provider": provider, "source": "provider_api",
                            "status": "ok" if models else "empty",
                            "models": sorted(models.values(), key=lambda model: model["model_id"]),
                        }
                    if not isinstance(cursor, str) or len(cursor) > 4096 or cursor in cursors:
                        raise DiscoveryError("invalid_response", "Provider returned an invalid pagination cursor.")
                    cursors.add(cursor)
                    params[cursor_param] = cursor
                raise DiscoveryError("pagination_limit", "Provider model list exceeded the page limit.")
    except (TimeoutError, httpx.TimeoutException):
        raise DiscoveryError("timeout", "Provider discovery timed out; retry later.", 504) from None
    except httpx.RequestError:
        raise DiscoveryError("network_error", "Could not reach the provider endpoint.") from None
    except (ValueError, UnicodeError):
        raise DiscoveryError("invalid_response", "Provider returned an invalid model list.") from None

"""OAuth2 flow for MCP server authentication."""

from __future__ import annotations

import asyncio
import hashlib
import secrets
import time
from typing import Any
from urllib.parse import urlencode

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()


class OAuthTokenStore:
    """In-memory token store with TTL support."""

    def __init__(self) -> None:
        self._tokens: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, server_url: str) -> dict[str, Any] | None:
        async with self._lock:
            entry = self._tokens.get(server_url)
            if entry is None:
                return None
            if entry.get("expires_at", 0) < time.time():
                del self._tokens[server_url]
                return None
            return entry

    async def set(self, server_url: str, token_data: dict[str, Any]) -> None:
        async with self._lock:
            if "expires_in" in token_data and "expires_at" not in token_data:
                token_data["expires_at"] = time.time() + token_data["expires_in"] - 60
            self._tokens[server_url] = token_data

    async def clear(self, server_url: str) -> None:
        async with self._lock:
            self._tokens.pop(server_url, None)


class OAuthFlow:
    """OAuth2 authorization code flow for MCP servers."""

    def __init__(
        self,
        client_id: str = "agent-engine",
        redirect_uri: str = "http://localhost:8000/oauth/callback",
        token_store: OAuthTokenStore | None = None,
    ) -> None:
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.token_store = token_store or OAuthTokenStore()
        self._code_verifiers: dict[str, str] = {}

    def _generate_pkce(self) -> tuple[str, str]:
        """Generate PKCE code verifier and challenge."""
        verifier = secrets.token_urlsafe(64)
        challenge = hashlib.sha256(verifier.encode()).hexdigest()
        return verifier, challenge

    async def get_authorization_url(
        self,
        server_url: str,
        authorization_endpoint: str,
        scopes: list[str] | None = None,
    ) -> str:
        """Build authorization URL with PKCE."""
        state = secrets.token_urlsafe(32)
        verifier, challenge = self._generate_pkce()
        self._code_verifiers[state] = verifier

        params: dict[str, str] = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        if scopes:
            params["scope"] = " ".join(scopes)

        url = f"{authorization_endpoint}?{urlencode(params)}"
        logger.info("Generated authorization url", server=server_url, state=state[:8])
        return url

    async def exchange_code(
        self,
        server_url: str,
        code: str,
        state: str,
        token_endpoint: str,
    ) -> dict[str, Any]:
        """Exchange authorization code for tokens."""
        verifier = self._code_verifiers.pop(state, None)
        if not verifier:
            raise ValueError("Invalid or expired state parameter")

        async with httpx.AsyncClient(timeout=settings.mcp_timeout) as client:
            response = await client.post(
                token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                    "client_id": self.client_id,
                    "code_verifier": verifier,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            token_data = response.json()

        await self.token_store.set(server_url, token_data)
        logger.info("Token exchange successful", server=server_url)
        return token_data

    async def refresh_token(self, server_url: str, token_endpoint: str) -> dict[str, Any]:
        """Refresh an expired access token."""
        existing = await self.token_store.get(server_url)
        if not existing or "refresh_token" not in existing:
            raise ValueError("No refresh token available")

        async with httpx.AsyncClient(timeout=settings.mcp_timeout) as client:
            response = await client.post(
                token_endpoint,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": existing["refresh_token"],
                    "client_id": self.client_id,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            token_data = response.json()

        await self.token_store.set(server_url, token_data)
        logger.info("Token refreshed", server=server_url)
        return token_data

    async def get_access_token(self, server_url: str, token_endpoint: str) -> str:
        """Get valid access token, refreshing if necessary."""
        entry = await self.token_store.get(server_url)
        if entry and "access_token" in entry:
            return entry["access_token"]

        try:
            new_tokens = await self.refresh_token(server_url, token_endpoint)
            return new_tokens["access_token"]
        except ValueError:
            raise ValueError(
                f"No valid token for {server_url}. Authorization required."
            ) from None

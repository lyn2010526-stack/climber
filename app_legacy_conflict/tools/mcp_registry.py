"""Client for MCP Registry (registry.nexus.ai)."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()

DEFAULT_REGISTRY_URL = "https://registry.nexus.ai/api"


class MCPRegistryClient:
    """Client for discovering MCP servers from public registry."""

    def __init__(self, base_url: str = DEFAULT_REGISTRY_URL) -> None:
        self.base_url = base_url.rstrip("/")

    async def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search for MCP servers by name or description."""
        try:
            async with httpx.AsyncClient(timeout=settings.mcp_timeout) as client:
                response = await client.get(
                    f"{self.base_url}/search",
                    params={"q": query, "limit": limit},
                )
                response.raise_for_status()
                data = response.json()
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and "servers" in data:
                    return data["servers"]
                return []
        except httpx.HTTPError as e:
            logger.warning("Registry search failed", query=query, error=str(e))
            return []

    async def get_server(self, name: str) -> dict[str, Any] | None:
        """Get detailed info about a specific MCP server."""
        try:
            async with httpx.AsyncClient(timeout=settings.mcp_timeout) as client:
                response = await client.get(f"{self.base_url}/servers/{name}")
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.warning("Registry get_server failed", name=name, error=str(e))
            return None
        except httpx.HTTPError as e:
            logger.warning("Registry get_server failed", name=name, error=str(e))
            return None

    async def list_popular(self, limit: int = 20) -> list[dict[str, Any]]:
        """List most popular MCP servers."""
        try:
            async with httpx.AsyncClient(timeout=settings.mcp_timeout) as client:
                response = await client.get(
                    f"{self.base_url}/popular",
                    params={"limit": limit},
                )
                response.raise_for_status()
                data = response.json()
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and "servers" in data:
                    return data["servers"]
                return []
        except httpx.HTTPError as e:
            logger.warning("Registry list_popular failed", error=str(e))
            return []

    async def list_categories(self) -> list[str]:
        """List available server categories."""
        try:
            async with httpx.AsyncClient(timeout=settings.mcp_timeout) as client:
                response = await client.get(f"{self.base_url}/categories")
                response.raise_for_status()
                data = response.json()
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and "categories" in data:
                    return data["categories"]
                return []
        except httpx.HTTPError as e:
            logger.warning("Registry list_categories failed", error=str(e))
            return []

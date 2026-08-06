"""MCP core registry and compatibility shim."""

from __future__ import annotations

from app.tools.mcp_cache import ToolResultCache
from app.tools.mcp_client import MCPClient, MCPRegistry, mcp_registry
from app.tools.mcp_health import AutoRestart, MCPHealthMonitor, McpStatus
from app.tools.mcp_models import (
    MCPContent,
    MCPPrompt,
    MCPResource,
    MCPTool,
    MCPToolResult,
)
from app.tools.mcp_oauth import OAuthFlow, OAuthTokenStore
from app.tools.mcp_registry import MCPRegistryClient
from app.tools.mcp_router import MCPRouter


class _MCPRegistry:
    """Backward-compatible registry wrapper."""

    def __init__(self) -> None:
        self._clients: dict[str, MCPClient] = {}
        self._registry = mcp_registry

    def register(self, plugin_id: str, client: MCPClient) -> None:
        self._clients[plugin_id] = client
        self._registry.register(client)

    def get_client(self, plugin_id: str) -> MCPClient | None:
        return self._clients.get(plugin_id)


mcp_registry_wrapper = _MCPRegistry()

__all__ = [
    "MCPClient",
    "MCPRegistry",
    "mcp_registry",
    "MCPContent",
    "MCPPrompt",
    "MCPResource",
    "MCPTool",
    "MCPToolResult",
    "OAuthFlow",
    "OAuthTokenStore",
    "MCPRegistryClient",
    "MCPHealthMonitor",
    "AutoRestart",
    "McpStatus",
    "ToolResultCache",
    "MCPRouter",
]

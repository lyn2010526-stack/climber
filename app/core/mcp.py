"""MCP core registry and compatibility shim."""

from __future__ import annotations

from app.tools.mcp_client import MCPClient


class _MCPRegistry:
    def __init__(self) -> None:
        self._clients: dict[str, MCPClient] = {}

    def register(self, plugin_id: str, client: MCPClient) -> None:
        self._clients[plugin_id] = client

    def get_client(self, plugin_id: str) -> MCPClient | None:
        return self._clients.get(plugin_id)


mcp_registry = _MCPRegistry()

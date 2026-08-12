"""Multi-server MCP tool routing."""

from __future__ import annotations

from typing import Any

import structlog

from app.tools.mcp_models import MCPTool, MCPToolResult

logger = structlog.get_logger()


class MCPRouter:
    """Route tool calls across multiple MCP servers."""

    def __init__(self) -> None:
        self.servers: dict[str, Any] = {}
        self._tool_index: dict[str, str] = {}

    def register_server(self, name: str, client: Any) -> None:
        """Register an MCP server client."""
        self.servers[name] = client
        self._rebuild_index()
        logger.info("MCP server registered", name=name)

    def unregister_server(self, name: str) -> None:
        """Remove an MCP server."""
        self.servers.pop(name, None)
        self._rebuild_index()
        logger.info("MCP server unregistered", name=name)

    def _rebuild_index(self) -> None:
        """Rebuild the tool-to-server index."""
        self._tool_index = {}
        for server_name, client in self.servers.items():
            tools = getattr(client, "tools", {})
            if isinstance(tools, dict):
                for tool_name in tools:
                    self._tool_index[tool_name] = server_name
                    self._tool_index[self.namespace_tool(server_name, tool_name)] = server_name

    async def route(self, tool_name: str, arguments: dict[str, Any]) -> MCPToolResult:
        """Route a tool call to the correct server."""
        server_name = self._tool_index.get(tool_name)
        if not server_name:
            namespaced = tool_name.replace("__", "/", 1) if "__" in tool_name else None
            if namespaced:
                server_name = self._tool_index.get(namespaced)

        if not server_name:
            return MCPToolResult(
                content=[{
                    "type": "text",
                    "text": f"Tool '{tool_name}' not found on any registered server",
                }],
                isError=True,
            )

        client = self.servers[server_name]
        try:
            if hasattr(client, "call_tool"):
                return await client.call_tool(tool_name, arguments)
            return MCPToolResult(
                content=[{
                    "type": "text",
                    "text": f"Server '{server_name}' does not support tool calls",
                }],
                isError=True,
            )
        except Exception as e:
            logger.error(
                "Tool routing failed",
                tool=tool_name,
                server=server_name,
                error=str(e),
            )
            return MCPToolResult(
                content=[{"type": "text", "text": f"Error: {e!s}"}],
                isError=True,
            )

    async def list_all_tools(self) -> dict[str, list[MCPTool]]:
        """List all tools grouped by server."""
        result: dict[str, list[MCPTool]] = {}
        for server_name, client in self.servers.items():
            try:
                if hasattr(client, "list_tools"):
                    tools = await client.list_tools()
                    result[server_name] = tools
                elif hasattr(client, "tools"):
                    tools = client.tools
                    if isinstance(tools, dict):
                        result[server_name] = list(tools.values())
                    elif isinstance(tools, list):
                        result[server_name] = tools
            except Exception as e:
                logger.warning(
                    "Failed to list tools",
                    server=server_name,
                    error=str(e),
                )
                result[server_name] = []
        return result

    @staticmethod
    def namespace_tool(server: str, tool: str) -> str:
        """Create namespaced tool name: server__tool."""
        return f"{server}__{tool}"

    def find_server_for_tool(self, tool_name: str) -> str | None:
        """Find which server provides a given tool."""
        return self._tool_index.get(tool_name)

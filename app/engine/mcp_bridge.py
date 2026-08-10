# app/engine/mcp_bridge.py
"""MCP Tool Bridge — auto-register MCP tools with usage descriptions.

When an MCP server connects, all its tools are automatically registered
into the unified ToolRuntime, including usage descriptions that get
injected into the model's system prompt.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MCPBridge:
    """Manages MCP server connections and tool registration."""

    def __init__(self, runtime):
        self.runtime = runtime
        self._servers: dict[str, Any] = {}
        self._tool_docs: dict[str, str] = {}

    async def connect_server(self, url: str, name: str, transport: str = "streamable_http") -> bool:
        """Connect to an MCP server and register all its tools."""
        try:
            from app.tools.mcp_client import MCPClient
            client = MCPClient(server_url=url, transport=transport)
            await client.connect()
            tools = await client.list_tools()
            for tool in tools:
                tool_name = f"{name}.{tool['name']}"
                await self._register_tool(client, tool, tool_name, tool["name"])
            self._servers[name] = {"url": url, "tools": tools, "client": client}
            logger.info("Connected MCP server '%s' with %d tools", name, len(tools))
            return True
        except Exception as e:
            logger.warning("Failed to connect MCP server '%s': %s", name, e)
            return False

    async def _register_tool(self, client, tool: dict, registered_name: str, original_name: str):
        """Register a single MCP tool into the runtime."""
        description = tool.get("description", original_name)

        async def handler(**kwargs):
            return await client.call_tool(original_name, kwargs)

        self.runtime.register_mcp_tool(
            name=registered_name,
            description=description,
            parameters=tool.get("inputSchema", {"type": "object", "properties": {}}),
            handler=handler,
            server=registered_name.split(".")[0],
        )
        self._tool_docs[registered_name] = f"- {registered_name}: {description}"

    def get_tool_descriptions_for_prompt(self) -> str:
        """Generate usage descriptions for system prompt injection."""
        if not self._tool_docs:
            return ""
        header = "## Available MCP Tools\n"
        tool_list = "\n".join(self._tool_docs.values())
        footer = "\n\nUse these tools when appropriate. Each tool's description explains when to use it."
        return f"{header}{tool_list}{footer}"

    async def disconnect_all(self):
        for _, server in self._servers.items():
            try:
                await server["client"].disconnect()
            except Exception:
                logger.debug("engine.mcp_bridge.suppressed", exc_info=True)
        self._servers.clear()
        self._tool_docs.clear()

    def list_servers(self) -> list[str]:
        return list(self._servers.keys())

    def list_tools_for_server(self, name: str) -> list[str]:
        if name not in self._servers:
            return []
        return [t["name"] for t in self._servers[name]["tools"]]

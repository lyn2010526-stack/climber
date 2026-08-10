"""Full-featured MCP client supporting multiple transports.

Supports stdio, streamable HTTP, and SSE transports with resources,
promissions, and tool routing.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import structlog
from mcp import ClientSession
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

from app.tools.mcp_models import (
    MCPContent,
    MCPPrompt,
    MCPResource,
    MCPTool,
    MCPToolResult,
)

logger = structlog.get_logger()


class MCPClient:
    """Full-featured MCP client supporting multiple transports.

    Usage:
        client = MCPClient(name="my-server", transport="stdio",
                           command="npx", args=["-y", "some-mcp-server"])
        await client.connect()
        tools = await client.list_tools()
        result = await client.call_tool("tool_name", {"arg": "value"})
        await client.close()
    """

    def __init__(
        self,
        name: str,
        transport: str = "stdio",
        command: str | None = None,
        args: list[str] | None = None,
        url: str | None = None,
        headers: dict[str, str] | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.name = name
        self.transport = transport
        self.command = command
        self.args = args or []
        self.url = url
        self.headers = headers or {}
        self.env = env or {}

        self.session: ClientSession | None = None
        self.tools: dict[str, MCPTool] = {}
        self.resources: dict[str, MCPResource] = {}
        self.prompts: dict[str, MCPPrompt] = {}
        self._server_info: dict[str, Any] = {}
        self._connect_cm: Any = None
        self._connect_ctx: Any = None
        self._notification_handlers: dict[str, list[Callable]] = {}

    @property
    def is_connected(self) -> bool:
        return self.session is not None

    async def connect(self) -> None:
        """Connect to MCP server using configured transport."""
        if self.transport == "stdio":
            await self._connect_stdio()
        elif self.transport == "streamable_http":
            await self._connect_http()
        elif self.transport == "sse":
            await self._connect_sse()
        else:
            raise ValueError(f"Unsupported transport: {self.transport}")

        logger.info(
            "MCP client connected",
            name=self.name,
            transport=self.transport,
        )

    async def _connect_stdio(self) -> None:
        """Connect via stdio transport."""
        from mcp.client.stdio import StdioServerParameters

        if not self.command:
            raise ValueError("stdio transport requires 'command' parameter")

        params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=self.env,
        )
        self._connect_cm = stdio_client(params)
        read, write = await self._connect_cm.__aenter__()

        self.session = ClientSession(read, write)
        await self.session.__aenter__()
        await self._initialize()

    async def _connect_http(self) -> None:
        """Connect via streamable HTTP transport."""
        if not self.url:
            raise ValueError("streamable_http transport requires 'url' parameter")

        self._connect_cm = streamablehttp_client(
            url=self.url,
            headers=self.headers,
        )
        read, write, _ = await self._connect_cm.__aenter__()

        self.session = ClientSession(read, write)
        await self.session.__aenter__()
        await self._initialize()

    async def _connect_sse(self) -> None:
        """Connect via SSE transport."""
        try:
            from mcp.client.sse import sse_client
        except ImportError:
            raise ImportError(
                "SSE transport requires mcp[sse] extra. "
                "Install with: pip install mcp[sse]"
            ) from None

        if not self.url:
            raise ValueError("sse transport requires 'url' parameter")

        self._connect_cm = sse_client(url=self.url, headers=self.headers)
        read, write = await self._connect_cm.__aenter__()

        self.session = ClientSession(read, write)
        await self.session.__aenter__()
        await self._initialize()

    async def _initialize(self) -> None:
        """Initialize session and discover capabilities."""
        if not self.session:
            raise RuntimeError("Session not established")

        result = await self.session.initialize()
        self._server_info = {
            "name": result.serverInfo.name,
            "version": result.serverInfo.version,
            "protocol_version": result.protocolVersion,
            "capabilities": result.capabilities.model_dump()
            if hasattr(result.capabilities, "model_dump")
            else {},
        }

        await self._discover_capabilities()

    async def _discover_capabilities(self) -> None:
        """Discover tools, resources, and prompts from server."""
        caps = self._server_info.get("capabilities", {})

        if "tools" in caps:
            try:
                raw_tools = await self.session.list_tools()
                self.tools = {}
                for t in raw_tools.tools:
                    self.tools[t.name] = MCPTool(
                        name=t.name,
                        title=getattr(t, "title", None),
                        description=t.description or "",
                        inputSchema=t.inputSchema,
                        annotations=getattr(t, "annotations", None),
                    )
            except Exception as e:
                logger.warning("Failed to list tools", server=self.name, error=str(e))

        if "resources" in caps:
            try:
                raw_resources = await self.session.list_resources()
                self.resources = {}
                for r in raw_resources.resources:
                    self.resources[r.uri] = MCPResource(
                        uri=r.uri,
                        name=r.name,
                        description=getattr(r, "description", None),
                        mimeType=getattr(r, "mimeType", None),
                    )
            except Exception as e:
                logger.warning("Failed to list resources", server=self.name, error=str(e))

        if "prompts" in caps:
            try:
                raw_prompts = await self.session.list_prompts()
                self.prompts = {}
                for p in raw_prompts.prompts:
                    args = None
                    if hasattr(p, "arguments") and p.arguments:
                        args = [
                            {"name": a.name, "description": getattr(a, "description", None)}
                            for a in p.arguments
                        ]
                    self.prompts[p.name] = MCPPrompt(
                        name=p.name,
                        description=getattr(p, "description", None),
                        arguments=args,
                    )
            except Exception as e:
                logger.warning("Failed to list prompts", server=self.name, error=str(e))

        logger.info(
            "MCP capabilities discovered",
            server=self.name,
            tools=len(self.tools),
            resources=len(self.resources),
            prompts=len(self.prompts),
        )

    async def list_tools(self) -> list[MCPTool]:
        """List available tools with pagination."""
        if not self.session:
            raise RuntimeError("Not connected")

        all_tools: list[MCPTool] = []
        cursor: str | None = None

        while True:
            kwargs: dict[str, Any] = {}
            if cursor:
                kwargs["cursor"] = cursor

            result = await self.session.list_tools(**kwargs)
            for t in result.tools:
                all_tools.append(MCPTool(
                    name=t.name,
                    title=getattr(t, "title", None),
                    description=t.description or "",
                    inputSchema=t.inputSchema,
                    annotations=getattr(t, "annotations", None),
                ))

            cursor = getattr(result, "nextCursor", None)
            if not cursor:
                break

        self.tools = {t.name: t for t in all_tools}
        return all_tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> MCPToolResult:
        """Call a tool with inputSchema validation."""
        if not self.session:
            raise RuntimeError("Not connected")

        tool_def = self.tools.get(name)
        if tool_def and tool_def.inputSchema:
            self._validate_arguments(name, arguments, tool_def.inputSchema)

        try:
            result = await self.session.call_tool(name, arguments)
            content = []
            for item in result.content:
                content.append(MCPContent(
                    type=getattr(item, "type", "text"),
                    text=getattr(item, "text", None),
                    data=getattr(item, "data", None),
                    mimeType=getattr(item, "mimeType", None),
                    uri=getattr(item, "uri", None),
                ))

            return MCPToolResult(
                content=content,
                isError=getattr(result, "isError", False),
            )
        except Exception as e:
            logger.error("Tool call failed", tool=name, server=self.name, error=str(e))
            return MCPToolResult(
                content=[MCPContent(type="text", text=f"Error: {e!s}")],
                isError=True,
            )

    @staticmethod
    def _validate_arguments(tool_name: str, arguments: dict[str, Any], schema: dict[str, Any]) -> None:
        """Validate arguments against JSON Schema (basic validation)."""
        if not isinstance(schema, dict):
            return

        schema_type = schema.get("type")
        if schema_type == "object":
            properties = schema.get("properties", {})
            required = schema.get("required", [])

            for req_field in required:
                if req_field not in arguments:
                    raise ValueError(
                        f"Tool '{tool_name}' missing required argument: {req_field}"
                    )

            for key in arguments:
                if key not in properties and schema.get("additionalProperties") is False:
                    raise ValueError(
                        f"Tool '{tool_name}' got unexpected argument: {key}"
                    )

    async def list_resources(self) -> list[MCPResource]:
        """List available resources."""
        if not self.session:
            raise RuntimeError("Not connected")

        result = await self.session.list_resources()
        resources = []
        for r in result.resources:
            resources.append(MCPResource(
                uri=r.uri,
                name=r.name,
                description=getattr(r, "description", None),
                mimeType=getattr(r, "mimeType", None),
            ))

        self.resources = {r.uri: r for r in resources}
        return resources

    async def read_resource(self, uri: str) -> str:
        """Read a resource by URI."""
        if not self.session:
            raise RuntimeError("Not connected")

        result = await self.session.read_resource(uri)
        parts = []
        for item in result.contents:
            if hasattr(item, "text"):
                parts.append(item.text)
            elif hasattr(item, "blob"):
                parts.append(f"[binary: {item.mimeType or 'unknown'}]")
        return "\n".join(parts)

    async def list_prompts(self) -> list[MCPPrompt]:
        """List available prompts."""
        if not self.session:
            raise RuntimeError("Not connected")

        result = await self.session.list_prompts()
        prompts = []
        for p in result.prompts:
            args = None
            if hasattr(p, "arguments") and p.arguments:
                args = [
                    {"name": a.name, "description": getattr(a, "description", None)}
                    for a in p.arguments
                ]
            prompts.append(MCPPrompt(
                name=p.name,
                description=getattr(p, "description", None),
                arguments=args,
            ))

        self.prompts = {p.name: p for p in prompts}
        return prompts

    async def get_prompt(self, name: str, arguments: dict[str, Any] | None = None) -> str:
        """Get a prompt template."""
        if not self.session:
            raise RuntimeError("Not connected")

        kwargs: dict[str, Any] = {"name": name}
        if arguments:
            kwargs["arguments"] = arguments

        result = await self.session.get_prompt(**kwargs)
        parts = []
        for msg in result.messages:
            content = getattr(msg, "content", None)
            if hasattr(content, "text"):
                parts.append(content.text)
            elif isinstance(content, dict):
                parts.append(content.get("text", ""))
        return "\n".join(parts)

    async def subscribe(self, channel: str, callback: Callable) -> None:
        """Subscribe to real-time notifications."""
        if channel not in self._notification_handlers:
            self._notification_handlers[channel] = []
        self._notification_handlers[channel].append(callback)

    async def unsubscribe(self, channel: str, callback: Callable) -> None:
        """Unsubscribe from notifications."""
        handlers = self._notification_handlers.get(channel, [])
        if callback in handlers:
            handlers.remove(callback)

    async def close(self) -> None:
        """Close connection and cleanup resources."""
        if self.session:
            try:
                await self.session.__aexit__(None, None, None)
            except Exception:
                logger.debug("tools.mcp_client.suppressed", exc_info=True)
            self.session = None

        if self._connect_cm:
            try:
                await self._connect_cm.__aexit__(None, None, None)
            except Exception:
                logger.debug("tools.mcp_client.suppressed", exc_info=True)
            self._connect_cm = None

        self._notification_handlers.clear()
        logger.info("MCP client closed", name=self.name)

    # -- Backward compatibility layer --

    async def start(self) -> None:
        """Legacy entry point for backward compatibility."""
        await self.connect()

    async def stop(self) -> None:
        """Legacy entry point for backward compatibility."""
        await self.close()

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Return tools in OpenAI function calling format (backward compat)."""
        result = []
        for _, tool in self.tools.items():
            result.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            })
        return result


class MCPRegistry:
    """Manage multiple MCP server connections."""

    def __init__(self) -> None:
        self._clients: dict[str, MCPClient] = {}

    def register(self, client: MCPClient) -> None:
        self._clients[client.name or "default"] = client

    async def start_all(self) -> None:
        for client in self._clients.values():
            try:
                await client.connect()
            except Exception as e:
                logger.error("MCP server start failed", name=client.name, error=str(e))

    async def stop_all(self) -> None:
        for client in self._clients.values():
            try:
                await client.close()
            except Exception as e:
                logger.warning("mcp_client.stop_all_error", error=str(e))
        self._clients.clear()

    def get_client(self, name: str) -> MCPClient | None:
        return self._clients.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        tools = []
        for client in self._clients.values():
            for _, tool in client.tools.items():
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema,
                    },
                })
        return tools


mcp_registry = MCPRegistry()

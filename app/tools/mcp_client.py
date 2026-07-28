"""MCP Client - connects to external MCP servers."""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from app.config import settings

logger = structlog.get_logger()


class MCPClient:
    """A minimal MCP (Model Context Protocol) client supporting stdio transport."""

    def __init__(
        self,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        name: str | None = None,
        url: str | None = None,
    ):
        self.name = name
        self.command = command
        self.args = args or []
        self.env = env
        self.url = url
        self._process: asyncio.subprocess.Process | None = None
        self._tools: list[dict[str, Any]] = []
        self._id_counter = 0

    async def connect(self) -> None:
        await self.start()

    async def start(self) -> None:
        """Start the MCP server subprocess."""
        if self.url:
            logger.info("MCP server URL mode", url=self.url, name=self.name)
            self._tools = []
            return
        self._process = await asyncio.create_subprocess_exec(
            self.command,
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self.env,
        )
        await self._rpc_call("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "agent-engine", "version": "0.1.0"},
        })
        resp = await self._rpc_call("tools/list", {})
        self._tools = resp.get("tools", [])
        logger.info("MCP server started", command=self.command, tools=len(self._tools))

    async def stop(self) -> None:
        """Kill the subprocess."""
        if self._process:
            self._process.kill()
            await self._process.wait()
            self._process = None

    @property
    def tools(self) -> list[dict[str, Any]]:
        return self._tools

    async def list_tools(self) -> list[dict[str, Any]]:
        return self._tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the MCP server."""
        resp = await self._rpc_call("tools/call", {"name": name, "arguments": arguments})
        content = resp.get("content", [])
        parts = []
        for item in content:
            if item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "\n".join(parts)

    async def _rpc_call(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON-RPC request and read response ( Content-Length framing )."""
        if not self._process or not self._process.stdin or not self._process.stdout:
            raise RuntimeError("MCP server not running")

        self._id_counter += 1
        req_id = self._id_counter
        body = __import__("json").dumps({
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params,
        })
        header = f"Content-Length: {len(body)}\r\n\r\n"
        self._process.stdin.write((header + body).encode())
        await self._process.stdin.drain()

        # Read response header
        while True:
            line = await asyncio.wait_for(
                self._process.stdout.readline(),
                timeout=settings.mcp_timeout,
            )
            if line.startswith(b"Content-Length:"):
                length = int(line.decode().split(":")[1].strip())
                # blank line
                await self._process.stdout.readline()
                body_bytes = await self._process.stdout.readexactly(length)
                return __import__("json").loads(body_bytes)

        return {}


class MCPRegistry:
    """Manage multiple MCP server connections."""

    def __init__(self):
        self._clients: dict[str, MCPClient] = {}

    def register(self, client: MCPClient) -> None:
        self._clients[client.name or "default"] = client

    async def start_all(self) -> None:
        for client in self._clients.values():
            try:
                await client.start()
            except Exception as e:
                logger.error("MCP server start failed", name=client.name, error=str(e))

    async def stop_all(self) -> None:
        for client in self._clients.values():
            try:
                await client.stop()
            except Exception:
                pass
        self._clients.clear()

    def get_client(self, name: str) -> MCPClient | None:
        return self._clients.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        tools = []
        for client in self._clients.values():
            tools.extend(client.tools)
        return tools


mcp_registry = MCPRegistry()

"""MCP data models for tools, resources, and prompts."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MCPTool(BaseModel):
    """MCP tool definition."""

    name: str
    title: str | None = None
    description: str
    inputSchema: dict[str, Any]
    annotations: dict[str, Any] | None = None


class MCPContent(BaseModel):
    """MCP content item."""

    type: str  # "text", "image", "resource", "audio"
    text: str | None = None
    data: str | None = None  # base64 for binary
    mimeType: str | None = None
    uri: str | None = None


class MCPToolResult(BaseModel):
    """MCP tool call result."""

    content: list[MCPContent]
    isError: bool = False

    def to_text(self) -> str:
        """Extract text content from result."""
        parts = []
        for item in self.content:
            if item.type == "text" and item.text:
                parts.append(item.text)
            elif item.type == "resource" and item.uri:
                parts.append(f"[resource: {item.uri}]")
        return "\n".join(parts)


class MCPResource(BaseModel):
    """MCP resource."""

    uri: str
    name: str
    description: str | None = None
    mimeType: str | None = None


class MCPPromptArgument(BaseModel):
    """MCP prompt argument definition."""

    name: str
    description: str | None = None
    required: bool = False


class MCPPrompt(BaseModel):
    """MCP prompt."""

    name: str
    description: str | None = None
    arguments: list[MCPPromptArgument] | None = None


class MCPServerInfo(BaseModel):
    """MCP server information."""

    name: str
    version: str
    protocol_version: str
    capabilities: dict[str, Any] = Field(default_factory=dict)


class MCPTransportType(str):
    """MCP transport type constants."""

    STDIO = "stdio"
    STREAMABLE_HTTP = "streamable_http"
    SSE = "sse"

"""Tool bridge for collaboration—unified access to built-in tools, Skills, and MCP."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.tools import tool_registry


@dataclass
class ToolResult:
    """Result of a tool execution."""

    success: bool
    output: str
    tool_name: str
    error: str | None = None


@dataclass
class ToolDefinition:
    """Simplified tool definition for function calling."""

    name: str
    description: str
    parameters: dict[str, Any]


class ToolBridge:
    """Unified tool access for collaboration members.

    Provides access to:
    - Built-in tools (web_search, read_file, write_file, etc.)
    - Skills (via skill tool registration)
    - MCP plugins (via MCP tool registration)
    """

    # Tools available to all roles
    SAFE_TOOLS = {
        "web_search", "fetch_url", "wikipedia_summary",
        "calculator", "translate", "summarize",
        "get_datetime", "base64_encode", "json_get",
    }

    # Tools restricted to Worker only
    WORKER_ONLY_TOOLS = {
        "read_file", "write_file", "list_files", "run_command",
        "generate_image",
    }

    def __init__(self, session_dir: str | None = None):
        self._session_dir = session_dir

    def list_tools(self, tool_names: list[str] | None = None, is_worker: bool = True) -> list[dict[str, Any]]:
        """List available tools in OpenAI function calling format.

        Args:
            tool_names: Specific tool names to include. None = all available.
            is_worker: If False, exclude worker-only tools.
        """
        result = []
        available = self._get_available_tools(is_worker)

        for name, defn in available.items():
            if tool_names and name not in tool_names:
                continue
            result.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": defn.description,
                    "parameters": defn.parameters,
                },
            })
        return result

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        """Execute a tool by name."""
        try:
            output = await tool_registry.execute(tool_name, arguments)
            return ToolResult(success=True, output=output, tool_name=tool_name)
        except Exception as e:
            return ToolResult(
                success=False,
                output=f"Error: {e!s}",
                tool_name=tool_name,
                error=str(e),
            )

    def _get_available_tools(self, is_worker: bool) -> dict[str, ToolDefinition]:
        """Get all available tool definitions."""
        available: dict[str, ToolDefinition] = {}

        for defn in tool_registry.list_tools():
            # Skip worker-only tools for reviewers
            if not is_worker and defn.name in self.WORKER_ONLY_TOOLS:
                continue
            available[defn.name] = ToolDefinition(
                name=defn.name,
                description=defn.description,
                parameters=defn.parameters,
            )

        return available

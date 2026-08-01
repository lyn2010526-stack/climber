"""Unified tool abstraction layer.

Provides a single interface for both MCP tools and local Skills,
enabling them to be registered, discovered, and executed uniformly.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


class ToolSource(str, Enum):
    """Where the tool originates from."""

    LOCAL = "local"
    MCP = "mcp"
    SKILL = "skill"
    PLUGIN = "plugin"


class ToolCategory(str, Enum):
    """Tool category for organization."""

    FILE = "file"
    SHELL = "shell"
    NETWORK = "network"
    SEARCH = "search"
    CODE = "code"
    BROWSER = "browser"
    DATABASE = "database"
    AI = "ai"
    SYSTEM = "system"
    CUSTOM = "custom"


@dataclass
class UnifiedToolDefinition:
    """Unified tool definition that works for both MCP and Skill tools."""

    name: str
    description: str
    parameters: dict[str, Any]
    source: ToolSource = ToolSource.LOCAL
    category: ToolCategory = ToolCategory.CUSTOM
    source_id: str = ""
    source_name: str = ""
    is_async: bool = True
    is_enabled: bool = True
    requires_permission: bool = False
    timeout_seconds: float = 30.0
    max_retries: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])

    def to_openai_format(self) -> dict[str, Any]:
        """Convert to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "source": self.source.value,
            "category": self.category.value,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "is_enabled": self.is_enabled,
            "requires_permission": self.requires_permission,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
        }


@dataclass
class UnifiedToolResult:
    """Unified tool execution result."""

    success: bool
    output: str = ""
    error: str = ""
    tool_name: str = ""
    duration_ms: float = 0.0
    source: ToolSource = ToolSource.LOCAL
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "tool_name": self.tool_name,
            "duration_ms": self.duration_ms,
            "source": self.source.value,
        }


ToolHandler = Callable[..., Awaitable[str] | str]


class UnifiedToolRegistry:
    """Unified registry for all tool types (local, MCP, skill, plugin)."""

    def __init__(self) -> None:
        self._tools: dict[str, UnifiedToolDefinition] = {}
        self._handlers: dict[str, ToolHandler] = {}
        self._skill_tools: dict[str, set[str]] = {}
        self._mcp_tools: dict[str, set[str]] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        handler: ToolHandler,
        source: ToolSource = ToolSource.LOCAL,
        category: ToolCategory = ToolCategory.CUSTOM,
        source_id: str = "",
        source_name: str = "",
        requires_permission: bool = False,
        timeout_seconds: float = 30.0,
        max_retries: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> UnifiedToolDefinition:
        """Register a tool with the unified interface."""
        tool_def = UnifiedToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            source=source,
            category=category,
            source_id=source_id,
            source_name=source_name,
            requires_permission=requires_permission,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            metadata=metadata or {},
        )
        self._tools[name] = tool_def
        self._handlers[name] = handler

        if source == ToolSource.SKILL:
            self._skill_tools.setdefault(source_id, set()).add(name)
        elif source == ToolSource.MCP:
            self._mcp_tools.setdefault(source_id, set()).add(name)

        return tool_def

    def unregister(self, name: str) -> bool:
        """Unregister a tool."""
        tool = self._tools.pop(name, None)
        if tool is None:
            return False
        self._handlers.pop(name, None)

        if tool.source == ToolSource.SKILL and tool.source_id in self._skill_tools:
            self._skill_tools[tool.source_id].discard(name)
        elif tool.source == ToolSource.MCP and tool.source_id in self._mcp_tools:
            self._mcp_tools[tool.source_id].discard(name)

        return True

    def get(self, name: str) -> UnifiedToolDefinition | None:
        """Get a tool definition by name."""
        return self._tools.get(name)

    def get_handler(self, name: str) -> ToolHandler | None:
        """Get a tool handler by name."""
        return self._handlers.get(name)

    def list_all(self) -> list[UnifiedToolDefinition]:
        """List all registered tools."""
        return list(self._tools.values())

    def list_enabled(self) -> list[UnifiedToolDefinition]:
        """List only enabled tools."""
        return [t for t in self._tools.values() if t.is_enabled]

    def list_by_source(self, source: ToolSource) -> list[UnifiedToolDefinition]:
        """List tools by source type."""
        return [t for t in self._tools.values() if t.source == source]

    def list_by_category(self, category: ToolCategory) -> list[UnifiedToolDefinition]:
        """List tools by category."""
        return [t for t in self._tools.values() if t.category == category]

    def list_by_skill(self, skill_id: str) -> list[UnifiedToolDefinition]:
        """List tools registered under a specific skill."""
        tool_names = self._skill_tools.get(skill_id, set())
        return [self._tools[n] for n in tool_names if n in self._tools]

    def list_by_mcp(self, mcp_id: str) -> list[UnifiedToolDefinition]:
        """List tools registered under a specific MCP server."""
        tool_names = self._mcp_tools.get(mcp_id, set())
        return [self._tools[n] for n in tool_names if n in self._tools]

    def set_enabled(self, name: str, enabled: bool) -> bool:
        """Enable or disable a tool."""
        tool = self._tools.get(name)
        if tool is None:
            return False
        tool.is_enabled = enabled
        return True

    def get_openai_tools(self, include_disabled: bool = False) -> list[dict[str, Any]]:
        """Get all tools in OpenAI function calling format."""
        tools = self.list_all() if include_disabled else self.list_enabled()
        return [t.to_openai_format() for t in tools]

    async def execute(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> UnifiedToolResult:
        """Execute a tool with unified error handling and timeout."""
        tool = self._tools.get(name)
        handler = self._handlers.get(name)

        if tool is None or handler is None:
            return UnifiedToolResult(
                success=False,
                error=f"Tool '{name}' not found",
                tool_name=name,
            )

        if not tool.is_enabled:
            return UnifiedToolResult(
                success=False,
                error=f"Tool '{name}' is disabled",
                tool_name=name,
                source=tool.source,
            )

        start = time.monotonic()
        last_error = ""

        for attempt in range(tool.max_retries + 1):
            try:
                if tool.is_async:
                    result = await asyncio.wait_for(
                        handler(**arguments),
                        timeout=tool.timeout_seconds,
                    )
                else:
                    result = handler(**arguments)

                duration = (time.monotonic() - start) * 1000
                return UnifiedToolResult(
                    success=True,
                    output=str(result),
                    tool_name=name,
                    duration_ms=duration,
                    source=tool.source,
                )
            except asyncio.TimeoutError:
                last_error = f"Tool '{name}' timed out after {tool.timeout_seconds}s"
                logger.warning("Tool timeout: %s (attempt %d)", name, attempt + 1)
            except Exception as e:
                last_error = str(e)
                logger.warning("Tool error: %s (attempt %d): %s", name, attempt + 1, e)

            if attempt < tool.max_retries:
                await asyncio.sleep(0.5 * (attempt + 1))

        duration = (time.monotonic() - start) * 1000
        return UnifiedToolResult(
            success=False,
            error=last_error,
            tool_name=name,
            duration_ms=duration,
            source=tool.source,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        stats: dict[str, Any] = {
            "total": len(self._tools),
            "enabled": sum(1 for t in self._tools.values() if t.is_enabled),
            "by_source": {},
            "by_category": {},
        }
        for source in ToolSource:
            count = sum(1 for t in self._tools.values() if t.source == source)
            if count > 0:
                stats["by_source"][source.value] = count
        for category in ToolCategory:
            count = sum(1 for t in self._tools.values() if t.category == category)
            if count > 0:
                stats["by_category"][category.value] = count
        return stats

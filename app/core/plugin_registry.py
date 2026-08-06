"""Plugin and tool registry for the agent engine."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Callable

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class PluginManifest(BaseModel):
    """Metadata describing a plugin that can be registered with the registry."""

    name: str
    version: str
    description: str = ""
    author: str = ""
    entry_point: str = ""
    dependencies: list[str] = Field(default_factory=list)
    enabled: bool = True
    icon: str | None = None


class ToolDefinition(BaseModel):
    """Definition of a tool available in the registry."""

    name: str
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    category: str = "general"
    enabled: bool = True
    timeout: float = 30.0


class PluginRegistry:
    """In-memory registry for plugins and tools with structlog logging."""

    def __init__(self) -> None:
        self._plugins: dict[str, PluginManifest] = {}
        self._tools: dict[str, ToolDefinition] = {}
        self._builtin_executors: dict[str, Callable[..., dict[str, Any]]] = {
            "calculate": self._calculate,
            "current_time": self._current_time,
            "echo": self._echo,
            "capitalize": self._capitalize,
        }
        self._logger = structlog.get_logger(__name__)

    async def register_plugin(self, manifest: PluginManifest) -> bool:
        """Register a plugin; returns False if the name is already taken."""
        if manifest.name in self._plugins:
            self._logger.info("plugin_register_skipped", name=manifest.name, reason="duplicate")
            return False
        self._plugins[manifest.name] = manifest
        self._logger.info("plugin_registered", name=manifest.name, version=manifest.version)
        return True

    async def unregister_plugin(self, name: str) -> bool:
        """Remove a plugin; returns False if it does not exist."""
        if name not in self._plugins:
            self._logger.info("plugin_unregister_missing", name=name)
            return False
        del self._plugins[name]
        self._logger.info("plugin_unregistered", name=name)
        return True

    async def list_plugins(self) -> list[PluginManifest]:
        """List all registered plugins."""
        return list(self._plugins.values())

    async def enable_plugin(self, name: str) -> bool:
        """Enable a plugin; returns False if it does not exist."""
        manifest = self._plugins.get(name)
        if manifest is None:
            self._logger.info("plugin_enable_missing", name=name)
            return False
        manifest.enabled = True
        self._logger.info("plugin_enabled", name=name)
        return True

    async def disable_plugin(self, name: str) -> bool:
        """Disable a plugin; returns False if it does not exist."""
        manifest = self._plugins.get(name)
        if manifest is None:
            self._logger.info("plugin_disable_missing", name=name)
            return False
        manifest.enabled = False
        self._logger.info("plugin_disabled", name=name)
        return True

    async def register_tool(self, definition: ToolDefinition) -> bool:
        """Register a tool; returns False if the name is already taken."""
        if definition.name in self._tools:
            self._logger.info("tool_register_skipped", name=definition.name, reason="duplicate")
            return False
        self._tools[definition.name] = definition
        self._logger.info("tool_registered", name=definition.name, category=definition.category)
        return True

    async def unregister_tool(self, name: str) -> bool:
        """Remove a tool; returns False if it does not exist."""
        if name not in self._tools:
            self._logger.info("tool_unregister_missing", name=name)
            return False
        del self._tools[name]
        self._logger.info("tool_unregistered", name=name)
        return True

    async def list_tools(self, category: str | None = None) -> list[ToolDefinition]:
        """List tools, optionally filtered by category."""
        if category is None:
            return list(self._tools.values())
        return [t for t in self._tools.values() if t.category == category]

    def get_tool(self, name: str) -> ToolDefinition | None:
        """Return a tool definition by name, or None if not found."""
        return self._tools.get(name)

    async def execute_tool(self, name: str, **kwargs: Any) -> dict[str, Any]:
        """Execute a builtin tool by name and return a result dictionary."""
        executor = self._builtin_executors.get(name)
        if executor is None:
            self._logger.warning("tool_execute_not_found", name=name)
            return {"error": "tool not found", "success": False}
        try:
            result = executor(**kwargs)
            result["success"] = True
            self._logger.info("tool_executed", name=name)
            return result
        except (TypeError, ValueError, ZeroDivisionError) as exc:
            self._logger.error("tool_execute_failed", name=name, error=str(exc))
            return {"error": str(exc), "success": False}

    def _calculate(self, a: float, b: float, op: str) -> dict[str, Any]:
        """Perform a basic arithmetic operation."""
        if op == "+":
            value = a + b
        elif op == "-":
            value = a - b
        elif op == "*":
            value = a * b
        elif op == "/":
            value = a / b
        else:
            raise ValueError(f"unsupported operator: {op}")
        return {"result": value}

    def _current_time(self) -> dict[str, Any]:
        """Return the current UTC timestamp."""
        return {"result": datetime.utcnow().isoformat() + "Z"}

    def _echo(self, text: str) -> dict[str, Any]:
        """Echo back the provided text."""
        return {"result": text}

    def _capitalize(self, text: str) -> dict[str, Any]:
        """Capitalize the provided text."""
        return {"result": text.capitalize()}


_registry_instance: PluginRegistry | None = None
_registry_lock = asyncio.Lock()


async def get_registry() -> PluginRegistry:
    """Return the process-wide singleton PluginRegistry instance."""
    global _registry_instance
    if _registry_instance is None:
        async with _registry_lock:
            if _registry_instance is None:
                _registry_instance = PluginRegistry()
                logger.info("plugin_registry_initialized")
    return _registry_instance

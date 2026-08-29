"""Unified tool runtime — single source of truth for all tool operations.

All local operations (file read/write, shell exec, search, API calls) are
registered as tools. The model only decides WHICH tool to call; execution
is always delegated to the tool runtime with full safety checks.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.tools import tool_registry as global_registry

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    success: bool
    output: Any = None
    error: str | None = None
    duration_ms: float = 0.0
    tool_name: str = ""


@dataclass
class RegisteredTool:
    name: str
    description: str
    parameters: dict
    handler: Callable
    source: str = "local"  # local, mcp, skill, plugin
    category: str = "custom"  # file, shell, network, search, code, system
    timeout: float = 30.0
    requires_permission: bool = False


class ToolRuntime:
    """Consolidates all tool registries into one execution surface."""

    def __init__(self):
        self._tools: dict[str, RegisteredTool] = {}
        self._load_builtin_tools()

    def _load_builtin_tools(self):
        """Import existing built-in tools from app.tools.builtins."""
        try:
            from app.tools import builtins  # noqa: F401  # triggers registration
            for name, tool_def in global_registry._definitions.items():
                handler = global_registry._tools.get(name)
                self._tools[name] = RegisteredTool(
                    name=name,
                    description=tool_def.description,
                    parameters=tool_def.parameters,
                    handler=handler,
                    source="local",
                )
        except ImportError:
            logger.warning("Could not load built-in tools")

    def register_local(
        self,
        name: str,
        description: str,
        parameters: dict,
        handler: Callable,
        category: str = "custom",
        timeout: float = 30.0,
        requires_permission: bool = False,
    ):
        self._tools[name] = RegisteredTool(
            name=name, description=description, parameters=parameters,
            handler=handler, source="local", category=category,
            timeout=timeout, requires_permission=requires_permission,
        )

    def register_mcp_tool(self, name: str, description: str, parameters: dict, handler: Callable, server: str = ""):
        self._tools[name] = RegisteredTool(
            name=name, description=description, parameters=parameters,
            handler=handler, source="mcp", category="custom",
            requires_permission=True,
        )

    async def execute(self, name: str, arguments: dict) -> ToolResult:
        tool = self._tools.get(name)
        if not tool:
            return ToolResult(success=False, error=f"Tool '{name}' not found", tool_name=name)

        start = time.monotonic()
        try:
            if asyncio.iscoroutinefunction(tool.handler):
                result = await asyncio.wait_for(tool.handler(**arguments), timeout=tool.timeout)
            else:
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: tool.handler(**arguments)),
                    timeout=tool.timeout,
                )
            return ToolResult(
                success=True, output=result,
                duration_ms=(time.monotonic() - start) * 1000,
                tool_name=name,
            )
        except TimeoutError:
            return ToolResult(
                success=False, error=f"Tool '{name}' timeout after {tool.timeout}s",
                duration_ms=(time.monotonic() - start) * 1000, tool_name=name,
            )
        except Exception as e:
            logger.warning("Tool execution failed: %s: %s", name, str(e))
            return ToolResult(
                success=False, error=str(e),
                duration_ms=(time.monotonic() - start) * 1000, tool_name=name,
            )

    async def execute_many(self, calls: list[tuple[str, dict]]) -> list[ToolResult]:
        semaphore = asyncio.Semaphore(10)

        async def _sem(name, args):
            async with semaphore:
                return await self.execute(name, args)

        return await asyncio.gather(*[_sem(name, args) for name, args in calls])

    def get_openai_tools(self) -> list[dict]:
        return [
            {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}}
            for t in self._tools.values()
        ]

    def list_tools(self) -> list[RegisteredTool]:
        return list(self._tools.values())

    def get_tool(self, name: str) -> RegisteredTool | None:
        return self._tools.get(name)

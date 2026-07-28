"""Tool system - registry, MCP client, and sandbox."""

from __future__ import annotations

import asyncio
import json
import subprocess
import textwrap
from typing import Any, Callable

import httpx
import structlog
from pydantic import BaseModel

from app.config import settings

logger = structlog.get_logger()


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema
    type: str = "function"  # function / mcp / http


class ToolRegistry:
    """Central registry for all available tools."""

    def __init__(self):
        self._tools: dict[str, Callable] = {}
        self._definitions: dict[str, ToolDefinition] = {}
        self._mcp_clients: list[Any] = []

    def register(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        func: Callable,
    ) -> None:
        """Register a callable tool."""
        self._tools[name] = func
        self._definitions[name] = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
        )
        logger.info("Tool registered", name=name)

    def register_mcp_tool(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        mcp_client: Any,
        mcp_tool_name: str,
    ) -> None:
        """Register an MCP tool that delegates to an MCP server."""
        async def _mcp_wrapper(**kwargs):
            return await mcp_client.call_tool(mcp_tool_name, kwargs)

        self._tools[name] = _mcp_wrapper
        self._definitions[name] = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            type="mcp",
        )
        logger.info("MCP tool registered", name=name, server=mcp_client.name)

    def unregister(self, name: str) -> bool:
        """Remove a tool from the registry."""
        if name in self._tools:
            del self._tools[name]
            del self._definitions[name]
            logger.info("Tool unregistered", name=name)
            return True
        return False

    def tool(
        self,
        name: str | None = None,
        description: str = "",
        parameters: dict[str, Any] | None = None,
    ) -> Callable:
        """Decorator to register a function as a tool."""

        def decorator(func: Callable) -> Callable:
            tool_name = name or func.__name__
            tool_desc = description or func.__doc__ or ""
            tool_params = parameters or self._infer_schema(func)
            self.register(tool_name, tool_desc, tool_params, func)
            return func

        return decorator

    def _infer_schema(self, func: Callable) -> dict[str, Any]:
        """Infer JSON Schema from function signature (basic)."""
        import inspect
        import typing

        sig = inspect.signature(func)
        # Resolve string annotations (from __future__ import annotations)
        hints = typing.get_type_hints(func)
        props: dict[str, Any] = {}
        required: list[str] = []
        for pname, param in sig.parameters.items():
            if pname in ("self", "cls"):
                continue
            prop: dict[str, Any] = {}
            annot = hints.get(pname, param.annotation)
            if annot is not inspect.Parameter.empty and annot is not None:
                # Handle Optional[X] -> X
                origin = getattr(annot, "__origin__", None)
                if origin is not None:
                    args = getattr(annot, "__args__", ())
                    if args:
                        annot = args[0]
                if annot is int or annot == int:
                    prop["type"] = "integer"
                elif annot is float or annot == float:
                    prop["type"] = "number"
                elif annot is bool or annot == bool:
                    prop["type"] = "boolean"
                else:
                    prop["type"] = "string"
            else:
                prop["type"] = "string"
            props[pname] = prop
            if param.default is inspect.Parameter.empty:
                required.append(pname)

        return {
            "type": "object",
            "properties": props,
            "required": required,
        }

    async def execute(self, name: str, arguments: dict[str, Any]) -> str:
        """Execute a registered tool."""
        func = self._tools.get(name)
        if not func:
            raise ValueError(f"Tool '{name}' not found")

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(**arguments)
            else:
                result = func(**arguments)
            return str(result) if not isinstance(result, str) else result
        except Exception as e:
            logger.error("Tool execution failed", tool=name, error=str(e))
            return f"Error executing {name}: {str(e)}"

    def get_openai_tools(self) -> list[dict[str, Any]]:
        """Return tools in OpenAI function calling format."""
        result = []
        for name, defn in self._definitions.items():
            result.append({
                "type": "function",
                "function": {
                    "name": defn.name,
                    "description": defn.description,
                    "parameters": defn.parameters,
                },
            })
        return result

    def list_tools(self) -> list[ToolDefinition]:
        return list(self._definitions.values())

    def get_tool(self, name: str) -> ToolDefinition | None:
        """Get a tool definition by name."""
        return self._definitions.get(name)


# Global singleton
tool_registry = ToolRegistry()


def register_builtins() -> None:
    """Import and register all built-in tools."""
    from app.tools import builtins  # noqa: F401


def tool(
    name: str | None = None,
    description: str = "",
    parameters: dict[str, Any] | None = None,
) -> Callable:
    """Convenience decorator using global registry."""
    return tool_registry.tool(name, description, parameters)

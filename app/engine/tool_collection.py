"""Collection of tools from various sources.

Provides a unified interface for managing tools from MCP servers,
Python functions, and other sources.
"""

from __future__ import annotations

import inspect
import typing
from collections.abc import Callable
from typing import Any, Protocol

import structlog

logger = structlog.get_logger()


class MCPClientProtocol(Protocol):
    """Protocol for MCP client compatibility."""

    name: str

    async def list_tools(self) -> list[dict[str, Any]]: ...

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str: ...


class ToolDefinition:
    """Definition of a tool."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        func: Callable,
        source: str = "function",
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.func = func
        self.source = source

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

    def to_anthropic_format(self) -> dict[str, Any]:
        """Convert to Anthropic tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }


class ToolCollection:
    """Collection of tools from various sources.

    Supports loading tools from MCP servers, Python functions,
    and manual registration.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    @classmethod
    def from_mcp(cls, mcp_client: MCPClientProtocol) -> ToolCollection:
        """Load tools from an MCP server.

        Connects to the MCP server, retrieves available tools,
        and wraps them for use by the agent.
        """
        collection = cls()

        try:
            import asyncio

            try:
                loop = asyncio.get_running_loop()
                tools = []
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        future = pool.submit(asyncio.run, mcp_client.list_tools())
                        tools = future.result(timeout=30)
                else:
                    tools = loop.run_until_complete(mcp_client.list_tools())
            except RuntimeError:
                tools = asyncio.run(mcp_client.list_tools())

            for tool in tools:
                name = tool.get("name", "")
                description = tool.get("description", "")
                parameters = tool.get("inputSchema", tool.get("parameters", {}))

                collection.add_tool(
                    name=name,
                    func=collection._make_mcp_wrapper(mcp_client, name),
                    description=description,
                    parameters=parameters,
                    source="mcp",
                )

            logger.info("tool_collection.mcp_loaded", count=len(tools), server=mcp_client.name)

        except Exception as e:
            logger.error("tool_collection.mcp_load_failed", error=str(e))

        return collection

    @classmethod
    def from_functions(cls, functions: dict[str, Callable]) -> ToolCollection:
        """Create a ToolCollection from a dict of Python functions.

        Infers JSON Schema from function signatures.
        """
        collection = cls()

        for name, func in functions.items():
            description = func.__doc__ or ""
            parameters = cls._infer_schema(func)
            collection.add_tool(
                name=name,
                func=func,
                description=description,
                parameters=parameters,
                source="function",
            )

        return collection

    @classmethod
    def from_definitions(
        cls,
        definitions: dict[str, dict[str, Any]],
    ) -> ToolCollection:
        """Create from a dict of name -> {func, description, parameters}."""
        collection = cls()

        for name, defn in definitions.items():
            collection.add_tool(
                name=name,
                func=defn["func"],
                description=defn.get("description", ""),
                parameters=defn.get("parameters", {}),
                source=defn.get("source", "function"),
            )

        return collection

    def add_tool(
        self,
        name: str,
        func: Callable,
        description: str = "",
        parameters: dict[str, Any] | None = None,
        source: str = "function",
    ) -> None:
        """Add a tool to the collection."""
        if parameters is None:
            parameters = self._infer_schema(func)

        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            func=func,
            source=source,
        )
        logger.debug("tool_collection.added", name=name, source=source)

    def remove_tool(self, name: str) -> bool:
        """Remove a tool from the collection."""
        if name in self._tools:
            del self._tools[name]
            logger.debug("tool_collection.removed", name=name)
            return True
        return False

    def get(self, name: str) -> ToolDefinition | None:
        """Get a tool definition by name."""
        return self._tools.get(name)

    def get_callable(self, name: str) -> Callable | None:
        """Get the callable for a tool."""
        tool = self._tools.get(name)
        return tool.func if tool else None

    def get_definitions(self, format: str = "openai") -> list[dict]:
        """Get tool definitions in the specified format."""
        if format == "openai":
            return [t.to_openai_format() for t in self._tools.values()]
        if format == "anthropic":
            return [t.to_anthropic_format() for t in self._tools.values()]
        raise ValueError(f"Unknown format: {format}")

    def list_tools(self) -> list[str]:
        """List all tool names."""
        return list(self._tools.values())

    @property
    def tools(self) -> dict[str, Callable]:
        """Get dict of name -> callable."""
        return {name: t.func for name, t in self._tools.items()}

    @property
    def definitions(self) -> dict[str, ToolDefinition]:
        """Get all tool definitions."""
        return dict(self._tools)

    async def execute(self, name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool by name with given arguments."""
        tool = self._tools.get(name)
        if not tool:
            return f"Error: Tool '{name}' not found"

        try:
            if inspect.iscoroutinefunction(tool.func):
                result = await tool.func(**arguments)
            else:
                result = tool.func(**arguments)
            return str(result) if not isinstance(result, str) else result
        except Exception as e:
            logger.error("tool_collection.execute_error", tool=name, error=str(e))
            return f"Error executing {name}: {str(e)}"

    @staticmethod
    def _make_mcp_wrapper(mcp_client: MCPClientProtocol, tool_name: str) -> Callable:
        """Create a wrapper function for an MCP tool."""
        async def wrapper(**kwargs: Any) -> str:
            return await mcp_client.call_tool(tool_name, kwargs)

        wrapper.__name__ = tool_name
        wrapper.__doc__ = f"MCP tool: {tool_name}"
        return wrapper

    @staticmethod
    def _infer_schema(func: Callable) -> dict[str, Any]:
        """Infer JSON Schema from function signature."""
        sig = inspect.signature(func)
        hints = typing.get_type_hints(func)

        props: dict[str, Any] = {}
        required: list[str] = []

        for pname, param in sig.parameters.items():
            if pname in ("self", "cls"):
                continue

            prop: dict[str, Any] = {}
            annot = hints.get(pname, param.annotation)

            if annot is not inspect.Parameter.empty and annot is not None:
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
                elif annot is list or annot == list:
                    prop["type"] = "array"
                elif annot is dict or annot == dict:
                    prop["type"] = "object"
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

"""Tool system - registry, MCP client, and sandbox."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import structlog
from pydantic import BaseModel

from app.tools.permissions import ToolPermissionGate

logger = structlog.get_logger()


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema
    type: str = "function"  # function / mcp / http


@dataclass
class ToolExecutionOutcome:
    """Structured tool outcome used by callers that need failure semantics."""

    result: str = ""
    error: str = ""
    success: bool = True

    @property
    def output(self) -> str:
        """Compatibility alias used by debug recovery integrations."""
        return self.result


class ToolRegistry:
    """Central registry for all available tools."""

    def __init__(self, permission_gate: "ToolPermissionGate | None" = None):
        self._tools: dict[str, Callable] = {}
        self._definitions: dict[str, ToolDefinition] = {}
        self._mcp_clients: list[Any] = []
        self._permission_gate = permission_gate

    def set_permission_gate(self, gate: "ToolPermissionGate | None") -> None:
        """Install (or clear) the dispatch-layer permission gate.

        Everything that reaches a tool goes through ``execute_result``, so this
        is the one place a DENY decision can be made binding. Without a gate the
        registry runs tools unconditionally, as before.
        """
        self._permission_gate = gate

    @property
    def permission_gate(self) -> "ToolPermissionGate | None":
        return self._permission_gate

    def _gate_error(self, name: str, arguments: dict[str, Any]) -> str | None:
        """Return the refusal message when the gate blocks this call."""
        gate = self._permission_gate
        if gate is None:
            return None
        try:
            verdict = gate.check(name, arguments)
        except Exception as exc:
            logger.error("Permission gate failed", tool=name, error=str(exc))
            return f"Permission gate error for {name}: {exc}"
        if verdict.blocked:
            logger.info("Tool call blocked by permission gate", tool=name, reason=verdict.reason)
            return verdict.reason
        return None

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
                if annot is int:
                    prop["type"] = "integer"
                elif annot is float:
                    prop["type"] = "number"
                elif annot is bool:
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
        """Execute a registered tool.

        Always returns a string (LLMs expect text responses from tools).
        Complex objects are serialized as JSON for structured parsing.
        """
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found")
        outcome = await self.execute_result(name, arguments)
        if outcome.success:
            return outcome.result
        return outcome.error

    async def execute_result(self, name: str, arguments: dict[str, Any]) -> ToolExecutionOutcome:
        """Execute a tool while preserving whether execution actually succeeded."""
        func = self._tools.get(name)
        if not func:
            return ToolExecutionOutcome(error=f"Tool '{name}' not found", success=False)

        blocked = self._gate_error(name, arguments)
        if blocked is not None:
            return ToolExecutionOutcome(error=blocked, success=False)

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(**arguments)
            else:
                result = func(**arguments)
            if isinstance(result, str):
                text = result
            elif isinstance(result, (dict, list)):
                import json
                text = json.dumps(result, ensure_ascii=False, default=str)
            else:
                text = str(result)
            return ToolExecutionOutcome(result=text)
        except Exception as e:
            logger.error("Tool execution failed", tool=name, error=str(e))
            return ToolExecutionOutcome(error=f"Error executing {name}: {str(e)}", success=False)

    def get_openai_tools(self) -> list[dict[str, Any]]:
        """Return tools in OpenAI function calling format."""
        result = []
        for _name, defn in self._definitions.items():
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


class SessionToolRegistry:
    """Read-through overlay adding per-session tools on top of a base registry.

    Session-scoped tools (e.g. recall) close over one session and must not
    leak into the shared global registry. This overlay answers lookups from
    the session-local set first, then falls back to the base registry, so the
    executor and ``build_tools`` see a single coherent registry per run.
    """

    def __init__(self, base: ToolRegistry) -> None:
        self._base = base
        self._local_tools: dict[str, Callable] = {}
        self._local_definitions: dict[str, ToolDefinition] = {}

    def add(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        func: Callable,
    ) -> None:
        self._local_tools[name] = func
        self._local_definitions[name] = ToolDefinition(
            name=name, description=description, parameters=parameters
        )

    def remove(self, name: str) -> None:
        self._local_tools.pop(name, None)
        self._local_definitions.pop(name, None)

    async def execute_result(self, name: str, arguments: dict[str, Any]) -> ToolExecutionOutcome:
        func = self._local_tools.get(name)
        if func is None:
            return await self._base.execute_result(name, arguments)
        blocked = self._base._gate_error(name, arguments)
        if blocked is not None:
            return ToolExecutionOutcome(error=blocked, success=False)
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(**arguments)
            else:
                result = func(**arguments)
            text = result if isinstance(result, str) else str(result)
            return ToolExecutionOutcome(result=text)
        except Exception as e:
            return ToolExecutionOutcome(error=f"Error executing {name}: {e}", success=False)

    async def execute(self, name: str, arguments: dict[str, Any]) -> str:
        outcome = await self.execute_result(name, arguments)
        return outcome.result if outcome.success else outcome.error

    def get_tool(self, name: str) -> ToolDefinition | None:
        return self._local_definitions.get(name) or self._base.get_tool(name)

    def list_tools(self) -> list[ToolDefinition]:
        merged = dict(self._base._definitions)
        merged.update(self._local_definitions)
        return list(merged.values())

    def get_openai_tools(self) -> list[dict[str, Any]]:
        merged: dict[str, ToolDefinition] = dict(self._base._definitions)
        merged.update(self._local_definitions)
        return [
            {
                "type": "function",
                "function": {
                    "name": defn.name,
                    "description": defn.description,
                    "parameters": defn.parameters,
                },
            }
            for defn in merged.values()
        ]


class ToolRegistryProvider:
    """Provides isolated tool registry instances.

    Use get_registry() for the global default, or create_isolated()
    for test/tenant-specific registries.
    """

    _global: ToolRegistry | None = None

    @classmethod
    def get_registry(cls) -> ToolRegistry:
        if cls._global is None:
            cls._global = ToolRegistry()
        return cls._global

    @classmethod
    def create_isolated(cls) -> ToolRegistry:
        return ToolRegistry()

    @classmethod
    def reset_global(cls) -> None:
        global tool_registry
        cls._global = None
        tool_registry = cls.get_registry()


def get_tool_registry() -> ToolRegistry:
    return ToolRegistryProvider.get_registry()


def create_isolated_registry() -> ToolRegistry:
    return ToolRegistryProvider.create_isolated()


tool_registry = ToolRegistryProvider.get_registry()


def tool(
    name: str | None = None,
    description: str = "",
    parameters: dict[str, Any] | None = None,
) -> Callable:
    """Convenience decorator using global registry."""
    return tool_registry.tool(name, description, parameters)


def register_builtins() -> None:
    """Import and register all built-in tools.

    Also installs the default permission gate on the global registry so a DENY
    decision from ``app/core/permission_rules.py`` binds every dispatch path,
    including callers that build ``ParallelToolExecutor`` without a validator.
    A registry that already has a gate keeps it.
    """
    from app.tools import builtins  # noqa: F401
    from app.tools import retrieval  # noqa: F401

    from app.tools.permissions import ToolPermissionGate, default_dispatch_config

    registry = get_tool_registry()
    if registry.permission_gate is None:
        registry.set_permission_gate(ToolPermissionGate(default_dispatch_config()))
        logger.info("Default permission gate installed on global tool registry")

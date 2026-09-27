"""Tool system - registry, MCP client, and sandbox."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from typing import Any

import structlog
from pydantic import BaseModel

logger = structlog.get_logger()


_SENSITIVE_ERROR_PATTERNS = (
    re.compile(
        r"(?i)(\b(?:api[_-]?key|authorization|password|passwd|secret|token)\b\s*[:=]\s*)((?:bearer\s+)?[^\s,;]+)"
    ),
    re.compile(r"(?i)(\bbearer\s+)([^\s,;]+)"),
    re.compile(r"\b(?:sk|rk)-[A-Za-z0-9_-]{12,}\b"),
)


def redact_error_text(error: BaseException) -> str:
    """Return exception text with common credential-shaped values removed."""
    text = str(error)
    for pattern in _SENSITIVE_ERROR_PATTERNS:
        if pattern.groups == 2:
            text = pattern.sub(r"\1[REDACTED]", text)
        else:
            text = pattern.sub("[REDACTED]", text)
    return text or type(error).__name__


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema
    type: str = "function"  # function / mcp / http


class ToolRegistry:
    """Central registry for all available tools."""

    # Tools that open a socket. Verified by scanning the registered callables
    # for httpx/requests/socket/playwright use, not by guessing from names:
    # download_file and translate were both silently missing, and the browser
    # tools drive Playwright, which egresses on the agent's behalf.
    # Enforced in execute(), so this set must stay in sync with reality.
    NETWORK_TOOLS: frozenset[str] = frozenset(
        {
            "web_search",
            "fetch_url",
            "get_weather",
            "wikipedia_summary",
            "generate_image",
            "download_file",
            "translate",
            "browser_navigate",
            "browser_screenshot",
            "browser_click",
            "browser_type",
            "browser_extract_links",
            "browser_extract_text",
            "open_browser",
            "take_screenshot",
            "click_mouse",
            "type_text",
        }
    )
    _network_enabled: bool = True

    @staticmethod
    def network_enabled_from_env() -> bool:
        """Read CLIMBER_ENABLE_NETWORK, failing closed on a bad value.

        An unparsable setting blocks egress: a typo in a security control must
        not silently restore network access.
        """
        import os

        raw = os.environ.get("CLIMBER_ENABLE_NETWORK")
        if raw is None or raw == "":
            return True
        return raw.strip().lower() in ("1", "true", "yes", "on")

    @classmethod
    def set_network_enabled(cls, enabled: bool) -> None:
        """Enable or disable outbound network access for registered tools."""
        cls._network_enabled = bool(enabled)

    @classmethod
    def network_enabled(cls) -> bool:
        return cls._network_enabled

    @classmethod
    def bootstrap_network_gate(cls) -> None:
        """Seed the gate from the environment at process start.

        Deliberately not called from ``__init__``: the gate is class-level
        state, and several production sites build a throwaway registry
        (workflow engine, collaboration, builtins). Seeding in the constructor
        meant the first such call re-read the environment and undid whatever
        the engine's sandbox had already decided, silently restoring egress.
        """
        cls._network_enabled = cls.network_enabled_from_env()

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

    @classmethod
    def _url_argument_keys(cls) -> frozenset[str]:
        """Argument names that carry a caller-supplied URL."""
        return frozenset({"url", "uri", "target", "link", "endpoint", "address", "host"})

    @classmethod
    def _check_url_arguments(cls, arguments: dict[str, Any]) -> str | None:
        """Return a refusal reason when an argument points at a blocked address.

        The egress gate above answers "may this deployment use the network at
        all". This answers "which address may it reach", which the gate cannot:
        ``fetch_url("http://169.254.169.254/latest/meta-data/")"`` is allowed
        egress and still steals cloud credentials. ``app.utils.ssrf`` held this
        logic but nothing called it, so the check runs here, on the single
        execution path every network tool already passes through.
        """
        if not isinstance(arguments, dict):
            return None

        from app.utils.ssrf import blocked_reason

        for key in cls._url_argument_keys():
            value = arguments.get(key)
            if not isinstance(value, str) or not value.strip():
                continue
            reason = blocked_reason(value)
            if reason is not None:
                return f"request blocked by SSRF protection ({reason})"
        return None

    async def execute(self, name: str, arguments: dict[str, Any]) -> str:
        """Execute a registered tool.

        Always returns a string (LLMs expect text responses from tools).
        Complex objects are serialized as JSON for structured parsing.
        """
        func = self._tools.get(name)
        if not func:
            raise ValueError(f"Tool '{name}' not found")

        if name in self.NETWORK_TOOLS and not self.network_enabled():
            logger.warning("Network tool blocked by egress gate", tool=name)
            return (
                f"Error executing {name}: network access is disabled for this "
                "deployment. Ask the user to enable it if network egress is required."
            )

        if name in self.NETWORK_TOOLS:
            refusal = self._check_url_arguments(arguments)
            if refusal is not None:
                logger.warning(
                    "Network tool blocked by SSRF guard", tool=name, reason=refusal
                )
                return f"Error executing {name}: {refusal}"

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(**arguments)
            else:
                result = func(**arguments)
            if isinstance(result, str):
                return result
            if isinstance(result, (dict, list)):
                import json
                return json.dumps(result, ensure_ascii=False, default=str)
            return str(result)
        except Exception as e:
            safe_error = redact_error_text(e)
            logger.error(
                "Tool execution failed",
                tool=name,
                error_type=type(e).__name__,
                error=safe_error,
            )  # noqa: TRY400 - keep traceback-free structured logging
            return f"Error executing {name}: {safe_error}"

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
        cls._global = None


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
    """Import and register all built-in tools."""
    import importlib

    # Imported for its registration side effect (@tool decorators populate the
    # registry); importlib states that without binding a name this returns.
    importlib.import_module("app.tools.builtins")

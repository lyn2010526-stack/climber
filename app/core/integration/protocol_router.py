"""Protocol router — unified routing across capability access protocols.

The agent calls capabilities without caring which protocol serves them: MCP,
A2A, Skill, local tool, HTTP, subagent, or model. The router maps a capability
request to the right transport adapter transparently.
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger()

PROTOCOL_MCP = "mcp"
PROTOCOL_A2A = "a2a"
PROTOCOL_SKILL = "skill"
PROTOCOL_TOOL = "tool"
PROTOCOL_HTTP = "http"
PROTOCOL_SUBAGENT = "subagent"
PROTOCOL_MODEL = "model"
PROTOCOL_LOCAL = "local"


class ProtocolRouter:
    """Routes capability invocations to their protocol adapter."""

    def __init__(self) -> None:
        self._handlers: dict[str, dict[str, Any]] = {}  # protocol -> {name -> handler}
        self._default_protocols: dict[str, str] = {}

    def register_handler(
        self, protocol: str, name: str, handler: Any
    ) -> None:
        self._handlers.setdefault(protocol, {})[name] = handler

    def set_default_protocol(self, capability_id: str, protocol: str) -> None:
        self._default_protocols[capability_id] = protocol

    def resolve_protocol(self, capability_id: str) -> str:
        return self._default_protocols.get(capability_id, PROTOCOL_TOOL)

    def list_capabilities(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for protocol, handlers in self._handlers.items():
            for name in handlers:
                result.append({"protocol": protocol, "name": name})
        return result

    def has(self, capability_id: str, protocol: str | None = None) -> bool:
        protocol = protocol or self.resolve_protocol(capability_id)
        return capability_id in self._handlers.get(protocol, {})

    async def call(self, capability_id: str, **kwargs: Any) -> Any:
        """Invoke a capability through its resolved protocol."""
        protocol = self.resolve_protocol(capability_id)
        handler = self._handlers.get(protocol, {}).get(capability_id)
        if handler is None:
            raise KeyError(
                f"capability '{capability_id}' not registered under protocol '{protocol}'"
            )
        result = handler(**kwargs)
        if hasattr(result, "__await__"):
            return await result
        return result


_default_router: ProtocolRouter | None = None


def get_protocol_router() -> ProtocolRouter:
    global _default_router
    if _default_router is None:
        _default_router = ProtocolRouter()
    return _default_router

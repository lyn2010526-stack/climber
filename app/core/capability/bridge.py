"""Bridge between the legacy ToolRegistry and the arch-v2 CapabilityRegistry.

Bulk-wraps every registered tool as a ``WrappedCapability`` so the capability
layer (routing, fallback, success-rate stats) governs real executions. The
wrapped callable is the tool's raw function — it never re-enters
``ToolRegistry.execute``, so there is no delegation recursion.
"""

from __future__ import annotations

import structlog

from app.core.capability.capability import CapabilityMeta, WrappedCapability
from app.core.capability.registry import CapabilityRegistry
from app.tools import ToolRegistry

logger = structlog.get_logger()

_KNOWN_TYPES = {"tool", "mcp", "http", "skill", "subagent", "model", "perception"}

#: Marks capabilities created by this bridge (idempotency + provenance).
BRIDGE_AUTHOR = "tool-bridge"


def register_tool_capabilities(
    registry: CapabilityRegistry, tool_registry: ToolRegistry
) -> int:
    """Wrap every tool in ``tool_registry`` as a capability. Idempotent.

    The capability id equals the tool name so routing and stats attach to
    the same identifier the LLM uses in tool calls.
    """
    registered = 0
    for defn in tool_registry.list_tools():
        existing = registry.get_implementations(defn.name)
        if any(impl.meta.author == BRIDGE_AUTHOR for impl in existing):
            continue
        fn = tool_registry._tools.get(defn.name)
        if fn is None:
            continue
        meta = CapabilityMeta(
            id=defn.name,
            name=defn.name,
            description=defn.description,
            capability_type=defn.type if defn.type in _KNOWN_TYPES else "tool",
            input_schema=defn.parameters,
            author=BRIDGE_AUTHOR,
        )
        registry.register(WrappedCapability(meta, fn))
        registered += 1
    logger.info("capability.tools_bridged", count=registered)
    return registered

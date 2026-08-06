"""Memory tool execution context.

Provides a ContextVar so memory tools can access the current
user_id and agent_id without changing the tool execution interface.
AgentEngine.run() sets this at the start of each execution.
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass

from app.core.principal import Principal, get_context_principal


@dataclass
class MemoryToolContext:
    user_id: str
    agent_id: str
    principal: Principal | None = None


# Set by AgentEngine at the start of each run(); read by memory tool wrappers.
memory_tool_ctx: contextvars.ContextVar[MemoryToolContext | None] = contextvars.ContextVar(
    "memory_tool_ctx", default=None,
)


def get_memory_tool_context() -> MemoryToolContext:
    """Return memory identity from tool context or the propagated principal."""
    ctx = memory_tool_ctx.get()
    if ctx is not None:
        return ctx
    principal = get_context_principal()
    return MemoryToolContext(
        user_id=principal.subject_id,
        agent_id="default-agent",
        principal=principal,
    )

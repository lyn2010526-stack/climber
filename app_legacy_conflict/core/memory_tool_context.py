"""Memory tool execution context.

Provides a ContextVar so memory tools can access the current
user_id and agent_id without changing the tool execution interface.
AgentEngine.run() sets this at the start of each execution.
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass


@dataclass
class MemoryToolContext:
    user_id: str
    agent_id: str


# Set by AgentEngine at the start of each run(); read by memory tool wrappers.
memory_tool_ctx: contextvars.ContextVar[MemoryToolContext | None] = contextvars.ContextVar(
    "memory_tool_ctx", default=None,
)


def get_memory_tool_context() -> MemoryToolContext:
    """Return the current memory tool context, falling back to defaults."""
    ctx = memory_tool_ctx.get()
    if ctx is None:
        return MemoryToolContext(user_id="default-user", agent_id="default-agent")
    return ctx

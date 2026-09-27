"""Context-local memory scope for self-editing memory tools.

Mirrors the ``current_agent_mode`` pattern in :mod:`app.core.file_patch`:
the engine binds the active session's ``user_id``/``agent_id`` into a
contextvar before running the iteration loop, so a plain-argument builtin tool
(e.g. ``core_memory_append``) can resolve *which* user's agent it is writing
for without those ids being supplied by the model. Keeping scope server-side
prevents the model from impersonating another user/agent via tool arguments.
"""

from __future__ import annotations

import contextvars

_current_user_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_memory_user_id", default=None
)
_current_agent_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_memory_agent_id", default=None
)


def set_memory_scope(user_id: str | None, agent_id: str | None) -> None:
    """Bind the active session's memory scope for tool execution context."""
    _current_user_id.set(user_id)
    _current_agent_id.set(agent_id)


def get_memory_scope() -> tuple[str | None, str | None]:
    """Return the bound ``(user_id, agent_id)`` or ``(None, None)`` if unset."""
    return _current_user_id.get(), _current_agent_id.get()


def clear_memory_scope() -> None:
    """Reset the bound scope (called when a session finishes)."""
    _current_user_id.set(None)
    _current_agent_id.set(None)

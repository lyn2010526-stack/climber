"""Process-wide access to the shared AgentEngine.

The engine singleton used to live in ``app/api/v1/chat.py``. Two modules under
``app/core/`` needed it (``reasoning/api.py``, ``group_collaboration.py``), and
reaching into the API layer for it made ``app.api.v1.__init__`` re-enter itself
while it was still executing, so ``import app.core.reasoning.api`` raised
``AttributeError: partially initialized module ... has no attribute 'router'``.

Keeping the accessor in ``app/core`` removes that cycle: the core layer no
longer depends on the API layer for a plain object reference.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.di import resolve as di_resolve

if TYPE_CHECKING:
    from app.core.agent_engine import AgentEngine

_engine: AgentEngine | None = None


def get_engine() -> AgentEngine:
    """Return the process-wide AgentEngine, constructing it on first use."""
    global _engine
    if _engine is None:
        from app.core.agent_engine import AgentEngine

        model_registry = di_resolve("ModelRegistry")
        tool_registry = di_resolve("ToolRegistry")
        _engine = AgentEngine(model_registry=model_registry, tool_registry=tool_registry)
    return _engine


def set_engine(engine: AgentEngine | None) -> None:
    """Replace the shared engine, used by tests and app startup."""
    global _engine
    _engine = engine

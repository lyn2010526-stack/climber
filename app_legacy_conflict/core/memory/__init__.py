"""Memory subpackage — persona, lifecycle, and cross-session inheritance.

Provides agent identity management, full memory lifecycle operations,
and personality inheritance across sessions.
"""

from app.core.memory.lifecycle import MemoryLifecycleManager
from app.core.memory.persona import (
    AgentPersona,
    PersonaStore,
    create_session_persona,
    get_effective_persona,
    merge_session_persona,
)

__all__ = [
    "AgentPersona",
    "PersonaStore",
    "MemoryLifecycleManager",
    "create_session_persona",
    "merge_session_persona",
    "get_effective_persona",
]

"""Group collaboration engine: supports sequential, hierarchical, and group_chat processes.

This module provides a facade over the collaboration subpackages.
All implementation has been extracted to app.core.collaboration.* modules.

Enhanced with CrewAI/AutoGen patterns:
- Task chaining and context passing
- Sequential, hierarchical, and group_chat processes
- Guardrails and output validation
- Checkpoint/resume
- Memory persistence
- Callbacks
- Human-in-the-loop
"""

from __future__ import annotations

from app.core.collaboration.base import GroupCollaborationEngine, get_group_collaboration_engine
from app.core.collaboration.constants import CALLBACK_REGISTRY, register_callback
from app.core.group_ws_hub import group_ws_hub

# Re-export for backward compatibility
__all__ = [
    "GroupCollaborationEngine",
    "get_group_collaboration_engine",
    "CALLBACK_REGISTRY",
    "register_callback",
    "group_ws_hub",
]

# Module-level singleton for direct import (lazy initialization)
group_collaboration_engine: GroupCollaborationEngine | None = None


def _get_engine_synchronously() -> GroupCollaborationEngine:
    """Get or create the engine synchronously for import-time access.

    Returns:
        The GroupCollaborationEngine instance.
    """
    global group_collaboration_engine
    if group_collaboration_engine is None:
        group_collaboration_engine = get_group_collaboration_engine()
    return group_collaboration_engine

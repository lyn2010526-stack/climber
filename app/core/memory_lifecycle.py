"""Memory lifecycle management.

Handles memory creation, reflection, and cleanup at turn and session boundaries.
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger()


class MemoryLifecycleManager:
    """Manages memory lifecycle events."""

    def __init__(
        self,
        memory_service: Any = None,
        reflection_service: Any = None,
    ) -> None:
        self.memory_service = memory_service
        self.reflection_service = reflection_service

    async def on_turn_complete(self, turn: Any, session: Any, message: str, result: Any) -> None:
        """Handle memory operations when a turn completes."""
        try:
            if self.memory_service and result and hasattr(result, 'content') and result.content and len(result.content) > 10:
                await self.memory_service.create_episodic_memory(
                    user_id=session.user_id,
                    content=f"User: {message}\nAssistant: {result.content[:500]}",
                    agent_id=session.agent_id,
                    source_session_id=session.session_id,
                    importance=0.7,
                )
        except Exception as e:
            logger.warning("memory_lifecycle.episodic_memory_creation_failed", error=str(e))

        try:
            if self.reflection_service:
                await self.reflection_service.maybe_reflect(session.user_id)
        except Exception as e:
            logger.warning("memory_lifecycle.reflection_failed", error=str(e))

    async def on_session_end(self, session: Any, messages: list[dict[str, str]]) -> None:
        """Handle memory operations when a session ends."""
        try:
            if self.memory_service:
                await self.memory_service.auto_extract_from_session(
                    user_id=session.user_id,
                    agent_id=session.agent_id,
                    session_id=session.session_id,
                    messages=messages,
                )
        except Exception as e:
            logger.warning("memory_lifecycle.session_end_extraction_failed", error=str(e))

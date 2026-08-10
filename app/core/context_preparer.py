"""Context preparation for agent execution.

Unifies memory retrieval and injection into a single preparation step,
replacing scattered memory injection code in AgentEngine.run().
"""

from __future__ import annotations

import logging
from typing import Any

from app.core import MessageRole
from app.core.hierarchical_memory import HierarchicalMemoryOrchestrator

logger = logging.getLogger(__name__)


class ContextPreparer:
    """Prepares agent context by retrieving and injecting memories.

    Replaces scattered memory injection code in AgentEngine.run() with
    a unified preparation step.
    """

    def __init__(
        self,
        memory_orchestrator: HierarchicalMemoryOrchestrator,
        core_memory_service: Any = None,
    ) -> None:
        self.memory_orchestrator = memory_orchestrator
        self.core_memory_service = core_memory_service

    async def prepare(self, session: Any, query: str) -> None:
        """Prepare context for the current query.

        Injects retrieved memories into session.messages as system messages.
        """
        try:
            # Unified memory retrieval via orchestrator
            result = await self.memory_orchestrator.retrieve_for_query(
                user_id=session.user_id,
                agent_id=session.agent_id,
                query=query,
                session_context={"messages": session.messages},
            )
            if result.core_memory or result.episodic_context or result.archival_context or result.reflection_context or result.user_profile:
                memory_text = result.format_for_prompt()
                session.messages.insert(-1, {"role": MessageRole.SYSTEM, "content": memory_text})
        except Exception as e:
            logger.debug("Context preparation failed: %s", e)

        # Inject Core Memory blocks as XML (kept separate for backward compatibility)
        if self.core_memory_service is not None:
            try:
                blocks = await self.core_memory_service.get_blocks(
                    user_id=session.user_id,
                    agent_id=session.agent_id,
                )
                if blocks:
                    xml = self.core_memory_service.format_for_prompt(blocks)
                    session.messages.insert(-1, {"role": MessageRole.SYSTEM, "content": xml})
            except Exception as e:
                logger.debug("Core memory injection failed: %s", e)

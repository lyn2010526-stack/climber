"""Memory tools for agent self-management.

Provides remember, recall, and forget tools that agents can call
to manage their own memories.
"""

from __future__ import annotations

import structlog
from typing import Any

from app.core.hierarchical_memory import HierarchicalMemoryOrchestrator

logger = structlog.get_logger()


class MemoryToolSet:
    """Memory tools for agent self-management."""

    def __init__(self, orchestrator: HierarchicalMemoryOrchestrator) -> None:
        self.orchestrator = orchestrator

    def get_tools(self) -> list[dict[str, Any]]:
        """Return tool definitions for the agent."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "remember",
                    "description": "Record important information to memory",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "The content to remember",
                            },
                            "importance": {
                                "type": "number",
                                "description": "Importance score between 0.0 and 1.0",
                                "minimum": 0.0,
                                "maximum": 1.0,
                            },
                            "memory_type": {
                                "type": "string",
                                "description": "Type of memory: episodic, semantic, or identity",
                                "enum": ["episodic", "semantic", "identity"],
                            },
                        },
                        "required": ["content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "recall",
                    "description": "Recall relevant memories for a query",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The query to search memories for",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of memories to return",
                                "default": 5,
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "forget",
                    "description": "Forget a specific memory by ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "memory_id": {
                                "type": "string",
                                "description": "The ID of the memory to forget",
                            },
                            "reason": {
                                "type": "string",
                                "description": "Reason for forgetting this memory",
                            },
                        },
                        "required": ["memory_id"],
                    },
                },
            },
        ]

    async def execute(self, tool_name: str, arguments: dict[str, Any], user_id: str, agent_id: str) -> str:
        """Execute a memory tool."""
        if tool_name == "remember":
            return await self._remember(arguments, user_id, agent_id)
        elif tool_name == "recall":
            return await self._recall(arguments, user_id, agent_id)
        elif tool_name == "forget":
            return await self._forget(arguments, user_id, agent_id)
        else:
            return f"Unknown memory tool: {tool_name}"

    async def _remember(self, arguments: dict[str, Any], user_id: str, agent_id: str) -> str:
        """Record a new memory."""
        content = arguments.get("content", "")
        if not content:
            return "Error: content is required"
        
        importance = float(arguments.get("importance", 0.5))
        memory_type = arguments.get("memory_type", "episodic")
        
        try:
            if memory_type == "episodic":
                await self.orchestrator._persistent_memory_service.create_episodic_memory(
                    user_id=user_id,
                    content=content,
                    agent_id=agent_id,
                    source_session_id="",
                    importance=importance,
                )
            elif memory_type == "semantic":
                await self.orchestrator._persistent_memory_service.create_archival_passage(
                    user_id=user_id,
                    text=content,
                    archive_id="default",
                )
            else:
                return f"Memory type '{memory_type}' not yet supported"
            return f"Remembered: {content[:100]}"
        except Exception as e:
            logger.error("memory_toolset.remember_failed", exc_info=True)
            return f"Error remembering: {e}"

    async def _recall(self, arguments: dict[str, Any], user_id: str, agent_id: str) -> str:
        """Recall relevant memories."""
        query = arguments.get("query", "")
        if not query:
            return "Error: query is required"
        
        limit = int(arguments.get("limit", 5))
        
        try:
            result = await self.orchestrator.retrieve_for_query(
                user_id=user_id,
                agent_id=agent_id,
                query=query,
                session_context=None,
            )
            if not any([result.core_memory, result.episodic_context, result.archival_context, getattr(result, 'reflection_context', '')]):
                return "No relevant memories found"
            return result.format_for_prompt()
        except Exception as e:
            logger.error("memory_toolset.recall_failed", exc_info=True)
            return f"Error recalling: {e}"

    async def _forget(self, arguments: dict[str, Any], user_id: str, agent_id: str) -> str:
        """Forget a specific memory."""
        memory_id = arguments.get("memory_id", "")
        if not memory_id:
            return "Error: memory_id is required"

        reason = arguments.get("reason", "no reason provided")

        try:
            from app.storage import async_session
            from app.storage.models_memory import EpisodicMemory
            from sqlalchemy import delete as sa_delete

            async with async_session() as db:
                result = await db.execute(
                    sa_delete(EpisodicMemory).where(
                        EpisodicMemory.id == memory_id,
                        EpisodicMemory.user_id == user_id,
                    )
                )
                await db.commit()
                deleted_count = result.rowcount or 0

            if self.orchestrator._vector_memory_service is not None:
                try:
                    await self.orchestrator._vector_memory_service.delete(
                        collection="episodic", doc_id=memory_id
                    )
                except Exception as e:
                    logger.warning("memory_toolset.forget_vector_delete", error=str(e))

            if deleted_count > 0:
                return f"Memory {memory_id} forgotten (reason: {reason})"
            return f"Memory {memory_id} not found or not owned by user"
        except Exception as e:
            logger.error("memory_toolset.forget_failed", error=str(e))
            return f"Error forgetting: {e}"

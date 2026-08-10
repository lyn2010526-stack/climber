"""Hierarchical memory system with on-demand retrieval.

Unifies core memory, episodic memory, archival memory, and reflection
into a single orchestration layer with token-budget-aware retrieval.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MemoryRetrievalConfig:
    """Configuration for memory retrieval budgets."""

    max_total_tokens: int = 4000
    core_memory_tokens: int = 1000
    episodic_memory_tokens: int = 1500
    archival_memory_tokens: int = 800
    reflection_tokens: int = 500
    user_profile_tokens: int = 200
    max_episodic_memories: int = 5
    max_archival_memories: int = 3
    max_reflections: int = 2
    recency_weight: float = 0.6
    relevance_weight: float = 0.4


@dataclass
class MemoryRetrievalResult:
    """Result of a memory retrieval operation."""

    core_memory: str = ""
    episodic_context: str = ""
    archival_context: str = ""
    reflection_context: str = ""
    user_profile: str = ""
    total_tokens: int = 0
    truncated: bool = False

    def format_for_prompt(self) -> str:
        """Format all retrieved memory for prompt injection."""
        parts: list[str] = []

        if self.core_memory:
            parts.append(self.core_memory)

        if self.user_profile:
            parts.append(f"[USER PROFILE]\n{self.user_profile}")

        if self.episodic_context:
            parts.append(f"[RELEVANT MEMORIES]\n{self.episodic_context}")

        if self.archival_context:
            parts.append(f"[ARCHIVAL KNOWLEDGE]\n{self.archival_context}")

        if self.reflection_context:
            parts.append(f"[PAST REFLECTIONS]\n{self.reflection_context}")

        return "\n\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "core_memory": self.core_memory[:200] if self.core_memory else "",
            "episodic_context": bool(self.episodic_context),
            "archival_context": bool(self.archival_context),
            "reflection_context": bool(self.reflection_context),
            "user_profile": bool(self.user_profile),
            "total_tokens": self.total_tokens,
            "truncated": self.truncated,
        }


class HierarchicalMemoryOrchestrator:
    """Orchestrates memory retrieval across all memory subsystems.

    Provides unified on-demand retrieval with token budget management.
    """

    def __init__(
        self,
        config: MemoryRetrievalConfig | None = None,
        core_memory: Any = None,
        persistent_memory: Any = None,
        vector_memory: Any = None,
        reflection: Any = None,
    ) -> None:
        self.config = config or MemoryRetrievalConfig()
        self._core_memory_service = core_memory
        self._persistent_memory_service = persistent_memory
        self._vector_memory_service = vector_memory
        self._reflection_service = reflection

    async def retrieve_for_query(
        self,
        user_id: str,
        agent_id: str,
        query: str,
        session_context: list[dict[str, str]] | None = None,
    ) -> MemoryRetrievalResult:
        """Retrieve all relevant memories for a query, respecting token budget."""
        result = MemoryRetrievalResult()
        remaining_tokens = self.config.max_total_tokens

        core_text = await self._retrieve_core_memory(user_id, agent_id)
        if core_text:
            core_tokens = len(core_text) // 4
            if core_tokens <= self.config.core_memory_tokens:
                result.core_memory = core_text
                remaining_tokens -= core_tokens
            else:
                result.core_memory = core_text[: self.config.core_memory_tokens * 4]
                remaining_tokens -= self.config.core_memory_tokens

        profile_text = await self._retrieve_user_profile(user_id)
        if profile_text and remaining_tokens > 0:
            profile_tokens = len(profile_text) // 4
            if profile_tokens <= min(self.config.user_profile_tokens, remaining_tokens):
                result.user_profile = profile_text
                remaining_tokens -= profile_tokens
            else:
                budget = min(self.config.user_profile_tokens, remaining_tokens)
                result.user_profile = profile_text[: budget * 4]
                remaining_tokens -= budget

        if remaining_tokens > 0:
            episodic_text, episodic_tokens = await self._retrieve_episodic(
                user_id, query, remaining_tokens
            )
            if episodic_text:
                result.episodic_context = episodic_text
                remaining_tokens -= episodic_tokens

        if remaining_tokens > 0:
            archival_text, archival_tokens = await self._retrieve_archival(
                user_id, query, remaining_tokens
            )
            if archival_text:
                result.archival_context = archival_text
                remaining_tokens -= archival_tokens

        if remaining_tokens > 0:
            reflection_text, reflection_tokens = await self._retrieve_reflections(
                user_id, query, remaining_tokens
            )
            if reflection_text:
                result.reflection_context = reflection_text
                remaining_tokens -= reflection_tokens

        result.total_tokens = self.config.max_total_tokens - remaining_tokens
        result.truncated = remaining_tokens <= 0

        return result

    async def _retrieve_core_memory(
        self, user_id: str, agent_id: str
    ) -> str:
        """Retrieve core memory blocks."""
        if self._core_memory_service is None:
            return ""
        try:
            blocks = await self._core_memory_service.get_blocks(
                user_id=user_id, agent_id=agent_id
            )
            if blocks:
                return self._core_memory_service.format_for_prompt(blocks)
        except Exception as e:
            logger.warning("Core memory retrieval failed: %s", e)
        return ""

    async def _retrieve_user_profile(self, user_id: str) -> str:
        """Retrieve user profile facts."""
        if self._persistent_memory_service is None:
            return ""
        try:
            return await self._persistent_memory_service.format_profile_for_prompt(user_id)
        except Exception as e:
            logger.warning("User profile retrieval failed: %s", e)
        return ""

    async def _retrieve_episodic(
        self, user_id: str, query: str, token_budget: int
    ) -> tuple[str, int]:
        """Retrieve relevant episodic memories within token budget."""
        if self._persistent_memory_service is None:
            return "", 0
        try:
            memories = await self._persistent_memory_service.retrieve_memories(
                user_id=user_id,
                query=query,
                limit=self.config.max_episodic_memories,
            )
            if not memories:
                return "", 0

            parts: list[str] = []
            used_tokens = 0
            for mem in memories:
                text = mem.content if hasattr(mem, "content") else mem.get("content", "")
                tokens = len(text) // 4
                if used_tokens + tokens > token_budget:
                    break
                parts.append(f"- {text}")
                used_tokens += tokens

            return "\n".join(parts), used_tokens
        except Exception as e:
            logger.warning("Episodic memory retrieval failed: %s", e)
        return "", 0

    async def _retrieve_archival(
        self, user_id: str, query: str, token_budget: int
    ) -> tuple[str, int]:
        """Retrieve archival memories within token budget."""
        if self._vector_memory_service is None:
            return "", 0
        try:
            results = await self._vector_memory_service.search(
                collection="archival",
                query=query,
                top_k=self.config.max_archival_memories,
            )
            if not results:
                return "", 0

            parts: list[str] = []
            used_tokens = 0
            for doc in results:
                text = doc.get("text", doc.get("content", ""))
                tokens = len(text) // 4
                if used_tokens + tokens > token_budget:
                    break
                parts.append(f"- {text}")
                used_tokens += tokens

            return "\n".join(parts), used_tokens
        except Exception as e:
            logger.warning("Archival memory retrieval failed: %s", e)
        return "", 0

    async def _retrieve_reflections(
        self, user_id: str, query: str, token_budget: int
    ) -> tuple[str, int]:
        """Retrieve relevant past reflections within token budget."""
        if self._reflection_service is None:
            return "", 0
        try:
            reflections = await self._reflection_service.get_similar_reflections(
                user_id=user_id,
                task_description=query,
                limit=self.config.max_reflections,
            )
            if not reflections:
                return "", 0

            parts: list[str] = []
            used_tokens = 0
            for ref in reflections:
                text = ref.get("text", ref.get("content", ""))
                tokens = len(text) // 4
                if used_tokens + tokens > token_budget:
                    break
                parts.append(f"- {text}")
                used_tokens += tokens

            return "\n".join(parts), used_tokens
        except Exception as e:
            logger.warning("Reflection retrieval failed: %s", e)
        return "", 0

    async def on_session_end(
        self,
        user_id: str,
        agent_id: str,
        session_id: str,
        messages: list[dict[str, str]],
    ) -> None:
        """Extract and store memories when a session ends."""
        if self._persistent_memory_service is not None:
            try:
                await self._persistent_memory_service.auto_extract_from_session(
                    user_id=user_id,
                    agent_id=agent_id,
                    session_id=session_id,
                    messages=messages,
                )
            except Exception as e:
                logger.warning("Auto memory extraction failed: %s", e)

    def get_config(self) -> MemoryRetrievalConfig:
        """Get current retrieval config."""
        return self.config

    def update_config(self, **kwargs: Any) -> None:
        """Update retrieval configuration."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

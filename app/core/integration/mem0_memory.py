"""Mem0 integration for unified memory management.

Provides persistent, searchable memory with Mem0's vector + graph storage,
seamlessly integrating with the existing memory subsystem.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from mem0 import Memory

logger = logging.getLogger(__name__)


class Mem0MemoryService:
    """Wrapper around Mem0 memory service with async support."""

    def __init__(
        self,
        collection_name: str = "agent_memory",
        user_id: str | None = None,
    ):
        self._collection = collection_name
        self._user_id = user_id
        self._client: Memory | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize Mem0 client."""
        try:
            self._client = Memory()
            self._initialized = True
            # stdlib logger 不支持自定义 kwargs（潜在 bug，已上报）。
            logger.info("mem0_initialized", collection=self._collection)  # type: ignore[call-arg]
        except Exception as exc:
            logger.warning("mem0_init_failed", error=str(exc))  # type: ignore[call-arg]
            self._initialized = False

    @property
    def is_available(self) -> bool:
        return self._initialized and self._client is not None

    async def add(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> str | None:
        """Add a memory entry."""
        if not self.is_available:
            return None
        assert self._client is not None

        try:
            result = self._client.add(
                content,
                user_id=user_id or self._user_id,
                metadata=metadata or {},
            )
            memory_id = (
                result.get("results", [{}])[0].get("id", "")
                if isinstance(result, dict)
                else str(result)
            )
            logger.debug("memory_added", memory_id=memory_id)  # type: ignore[call-arg]
            return memory_id
        except Exception as exc:
            logger.warning("memory_add_failed", error=str(exc))  # type: ignore[call-arg]
            return None

    async def search(
        self,
        query: str,
        limit: int = 10,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search memories by semantic similarity."""
        if not self.is_available:
            return []
        assert self._client is not None

        try:
            results = self._client.search(
                query,
                user_id=user_id or self._user_id,
                limit=limit,
            )
            if isinstance(results, dict):
                return cast(list[dict[str, Any]], results.get("results", []))
            return results if isinstance(results, list) else []
        except Exception as exc:
            logger.warning("memory_search_failed", error=str(exc))  # type: ignore[call-arg]
            return []

    async def get_all(
        self,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get all memories for a user."""
        if not self.is_available:
            return []
        assert self._client is not None

        try:
            results = self._client.get_all(user_id=user_id or self._user_id)
            if isinstance(results, dict):
                return cast(list[dict[str, Any]], results.get("results", []))
            return results if isinstance(results, list) else []
        except Exception as exc:
            logger.warning("memory_get_all_failed", error=str(exc))  # type: ignore[call-arg]
            return []

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        if not self.is_available:
            return False
        assert self._client is not None

        try:
            self._client.delete(memory_id)
            return True
        except Exception as exc:
            logger.warning("memory_delete_failed", error=str(exc))  # type: ignore[call-arg]
            return False

    async def delete_all(self, user_id: str | None = None) -> bool:
        """Delete all memories for a user."""
        if not self.is_available:
            return False
        assert self._client is not None

        try:
            self._client.delete_all(user_id=user_id or self._user_id)
            return True
        except Exception as exc:
            logger.warning("memory_delete_all_failed", error=str(exc))  # type: ignore[call-arg]
            return False


# Global service instance
_service: Mem0MemoryService | None = None


def get_mem0_service(
    collection_name: str = "agent_memory",
    user_id: str | None = None,
) -> Mem0MemoryService:
    """Get or create the global Mem0 service."""
    global _service
    if _service is None:
        _service = Mem0MemoryService(
            collection_name=collection_name,
            user_id=user_id,
        )
    return _service

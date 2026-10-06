"""Unified directory-scoped semantic index.

Every record carries ``dir`` (its scope) and ``level`` metadata so retrieval
can constrain to a directory instead of scanning the whole index. Chroma
failures degrade to logs; callers own the keyword fallback path.
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger()

_SEMANTIC_COLLECTION = "semantic"


class SemanticIndex:
    """Thin adapter over ``vector_memory`` for directory-scoped records."""

    def __init__(self, *, collection: str = _SEMANTIC_COLLECTION, enabled: bool = True) -> None:
        self._collection = collection
        self._enabled = enabled

    @property
    def collection(self) -> str:
        return self._collection

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def index(
        self,
        text: str,
        *,
        scope: str,
        level: int,
        doc_id: str,
        user_id: str,
        **extra: Any,
    ) -> bool:
        """Register one semantic record scoped to ``scope`` (best effort)."""
        if not self._enabled or not text.strip():
            return False
        try:
            from app.core.vector_memory import vector_memory

            metadata: dict[str, Any] = {"user_id": user_id, "dir": scope, "level": level}
            metadata.update(extra)
            await vector_memory.add(self._collection, doc_id, text, metadata=metadata)
        except Exception as exc:
            logger.warning("semantic_index_add_failed", scope=scope, doc_id=doc_id, error=str(exc))
            return False
        return True

    async def search(
        self,
        user_id: str,
        scope: str,
        query: str,
        *,
        level: int | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Vector search restricted to one user's directory scope."""
        if not self._enabled or not query.strip():
            return []
        try:
            from app.core.vector_memory import vector_memory
        except Exception:
            return []
        where: dict[str, Any] = {"$and": [{"user_id": user_id}, {"dir": scope}]}
        if level is not None:
            where["$and"].append({"level": level})
        try:
            return await vector_memory.search(self._collection, query, top_k=top_k, where=where)
        except Exception as exc:
            logger.warning("semantic_index_search_failed", scope=scope, error=str(exc))
            return []


# Global singleton
semantic_index = SemanticIndex()

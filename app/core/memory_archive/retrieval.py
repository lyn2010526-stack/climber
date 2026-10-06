"""Directory-scoped semantic retrieval.

``DirectoryRetriever`` resolves a scope first, then queries only records that
belong to that directory (vector ``dir`` metadata or DB sidecar rows) instead
of scanning the whole index. A deterministic keyword pass over the scope's own
sidecars keeps the path working when the vector index is unavailable.
"""

from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy import select

from app.core.memory_archive.index import SemanticIndex, semantic_index
from app.storage import async_session
from app.storage.models_memory_archive import MemorySidecar

logger = structlog.get_logger()

LEVEL_NAMES = {0: "abstract", 1: "overview", 2: "detail"}


def normalize_scope(scope: str) -> str:
    """Resolve a directory/scope string to its canonical form."""
    scope = (scope or "").strip().strip("/")
    if not scope:
        raise ValueError("scope must not be empty")
    return scope


class DirectoryRetriever:
    """Retrieve semantic records inside one user's directory scope."""

    def __init__(self, semantic: SemanticIndex | None = None) -> None:
        self._semantic = semantic or semantic_index

    async def search(
        self,
        user_id: str,
        scope: str,
        query: str,
        *,
        level: int | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """Vector search within the scope merged with its own sidecar matches."""
        scope = normalize_scope(scope)
        results: list[dict[str, Any]] = []
        seen: set[str] = set()

        for hit in await self._semantic.search(
            user_id, scope, query, level=level, top_k=max(top_k, 8),
        ):
            doc_id = str(hit.get("id", ""))
            if not doc_id or doc_id in seen:
                continue
            seen.add(doc_id)
            meta = hit.get("metadata") or {}
            results.append({
                "id": doc_id,
                "kind": "semantic",
                "level": meta.get("level", 2),
                "scope": scope,
                "text": hit.get("text", ""),
                "metadata": meta,
                "score": round(float(hit.get("score", 0.0)), 4),
            })

        for sidecar in await self._search_sidecars(
            user_id, scope, query, level=level, limit=top_k,
        ):
            if sidecar["id"] in seen:
                continue
            seen.add(sidecar["id"])
            results.append(sidecar)

        results.sort(key=lambda item: item.get("score", 0.0), reverse=True)
        return {
            "scope": scope,
            "query": query,
            "level": level,
            "total": len(results),
            "hits": results[: top_k],
        }

    async def find_sidecars(
        self,
        user_id: str,
        scope: str,
        query: str | None = None,
        *,
        level: int | None = None,
        limit: int = 10,
    ) -> list[MemorySidecar]:
        """Return the scope's L0/L1 sidecars, optionally filtered by keyword."""
        scope = normalize_scope(scope)
        async with async_session() as db:
            stmt = select(MemorySidecar).where(
                MemorySidecar.user_id == user_id,
                MemorySidecar.scope == scope,
            )
            if level is not None:
                stmt = stmt.where(MemorySidecar.level == level)
            stmt = stmt.order_by(MemorySidecar.level.asc()).limit(limit)
            rows = list((await db.execute(stmt)).scalars().all())
        if query:
            query_lower = query.lower()
            rows = [row for row in rows if query_lower in row.body.lower()]
        return rows

    async def _search_sidecars(
        self,
        user_id: str,
        scope: str,
        query: str,
        *,
        level: int | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        query_lower = (query or "").lower()
        hits: list[dict[str, Any]] = []
        rows = await self.find_sidecars(user_id, scope, level=level, limit=limit)
        for row in rows:
            body_lower = row.body.lower()
            matched = not query_lower or query_lower in body_lower
            if not matched:
                continue
            hits.append({
                "id": row.id,
                "kind": "sidecar",
                "level": row.level,
                "scope": row.scope,
                "text": row.body,
                "score": 1.0 if query_lower and query_lower in body_lower else 0.5,
            })
        return hits[:limit]

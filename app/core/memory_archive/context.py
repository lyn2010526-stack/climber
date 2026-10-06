"""Bypass context bundle: inject only L0/L1 summaries plus top memory hits.

A pure read path that never touches the Pi baseline loop: it assembles a
compact Markdown block an outer hook may attach to a conversation, keeping the
agent's standing context small while preserving recall of archived knowledge.
"""

from __future__ import annotations

from typing import Any

import structlog

from app.core.memory_archive.layers import MemorySidecarService, sidecar_service
from app.core.memory_archive.retrieval import DirectoryRetriever

logger = structlog.get_logger()

DEFAULT_SCOPES = ("reference", "skills", "conversations", "memories")


class MemoryContextBypass:
    """Assemble a token-cheap summary bundle for a user's session."""

    def __init__(
        self,
        *,
        sidecars: MemorySidecarService | None = None,
        retriever: DirectoryRetriever | None = None,
    ) -> None:
        self._sidecars = sidecars or sidecar_service
        self._retriever = retriever or DirectoryRetriever()

    async def build(
        self,
        user_id: str,
        query: str = "",
        *,
        scopes: tuple[str, ...] | list[str] | None = None,
        include_l1: bool = False,
        memory_top_k: int = 3,
    ) -> dict[str, Any]:
        """Return an injected summary block plus the supporting hits.

        Only L0 abstracts are injected by default; L1 overviews are opt-in so
        the standing context stays small. Memory hits are gathered from the
        memories scope for the current query.
        """
        selected = tuple(scopes or DEFAULT_SCOPES)
        summaries: list[dict[str, Any]] = []
        for scope in selected:
            l0, l1 = await self._sidecars.read_pair(user_id, scope)
            if l0 is None:
                continue
            summaries.append({
                "scope": scope,
                "abstract": l0.body,
                "overview": l1.body if include_l1 and l1 is not None else "",
            })
        hits: list[dict[str, Any]] = []
        if query and "memories" in selected:
            result = await self._retriever.search(user_id, "memories", query, level=2, top_k=memory_top_k)
            for hit in result["hits"]:
                meta = hit.get("metadata") or {}
                hits.append({
                    "memory_type": meta.get("memory_type", "memory"),
                    "content": hit.get("text", ""),
                })
        return {
            "content": self._render(summaries, include_l1=include_l1),
            "injected_summaries": len(summaries),
            "memory_hits": len(hits),
            "scopes": summaries,
            "hits": hits,
        }

    @staticmethod
    def _render(summaries: list[dict[str, Any]], *, include_l1: bool = False) -> str:
        if not summaries:
            return ""
        lines = ["## Archived Memory Context"]
        for item in summaries:
            lines.append(f"\n### {item['scope']}")
            lines.append(item["abstract"])
            if include_l1 and item.get("overview"):
                lines.append(f"\n{item['overview']}")
        return "\n".join(lines)


# Global singleton
memory_context_bypass = MemoryContextBypass()

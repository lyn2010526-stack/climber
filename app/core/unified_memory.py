"""Unified memory service — five-tier memory management for the agent engine.

Layers:
- L1 WORKING: short-lived working memory
- L2 EPISODIC: conversation events and experiences
- L3 SEMANTIC: facts and knowledge, backed by Mem0 when available
- L4 PROCEDURAL: skills, procedures, and learned behaviors

The service keeps an in-memory store for all tiers, mirrors the semantic tier
into Mem0 (or ChromaDB vector store when Mem0 is unavailable), deduplicates by
content fingerprint, and merges near-duplicate entries during consolidation.
"""

from __future__ import annotations

import asyncio
import difflib
import hashlib
import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

from app.core.integration.mem0_memory import get_mem0_service
from app.core.vector_memory import vector_memory

logger = structlog.get_logger(__name__)


class MemoryTier(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"

    @property
    def level(self) -> int:
        return {
            MemoryTier.WORKING: 1,
            MemoryTier.EPISODIC: 2,
            MemoryTier.SEMANTIC: 3,
            MemoryTier.PROCEDURAL: 4,
        }[self]


class MemoryEntry(BaseModel):
    id: str
    content: str
    tier: MemoryTier
    score: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    last_accessed_at: datetime | None = None


class UnifiedMemoryService:
    """Unified service over the L1-L4 memory tiers."""

    _VECTOR_COLLECTION = "archival"

    def __init__(self, user_id: str = "unified_memory") -> None:
        self._memories: dict[str, MemoryEntry] = {}
        self._fingerprints: dict[str, str] = {}
        self._mem0 = get_mem0_service(user_id=user_id)
        self._user_id = user_id
        self._mem0_tried = False

    async def _ensure_mem0(self) -> None:
        if self._mem0_tried:
            return
        self._mem0_tried = True
        try:
            await self._mem0.initialize()
        except Exception as exc:
            logger.warning("mem0_ensure_failed", error=str(exc))

    @staticmethod
    def _fingerprint(content: str) -> str:
        return hashlib.sha256(content.strip().lower().encode("utf-8")).hexdigest()

    @staticmethod
    def _clamp_score(score: Any) -> float:
        try:
            value = float(score)
        except (TypeError, ValueError):
            return 0.5
        return max(0.0, min(1.0, value))

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        return difflib.SequenceMatcher(None, a, b).ratio()

    def _from_mem0_result(self, item: dict[str, Any]) -> MemoryEntry | None:
        text = item.get("memory") or item.get("text") or ""
        if not text:
            return None
        mem0_id = str(item.get("id", ""))
        return MemoryEntry(
            id=mem0_id or str(uuid.uuid4()),
            content=text,
            tier=MemoryTier.SEMANTIC,
            score=self._clamp_score(item.get("score", 0.5)),
            metadata={"mem0_id": mem0_id, "source": "mem0"},
            created_at=datetime.now(UTC),
            last_accessed_at=datetime.now(UTC),
        )

    async def store(
        self,
        content: str,
        tier: MemoryTier,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        content = content.strip()
        if not content:
            raise ValueError("memory content must not be empty")

        fingerprint = self._fingerprint(content)
        existing_id = self._fingerprints.get(fingerprint)
        if existing_id is not None and existing_id in self._memories:
            logger.info(
                "memory_dedup_skipped",
                memory_id=existing_id,
                tier=tier.value,
                fingerprint=fingerprint[:12],
            )
            return self._memories[existing_id]

        now = datetime.now(UTC)
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            content=content,
            tier=tier,
            score=self._clamp_score((metadata or {}).get("score", 0.5)),
            metadata=dict(metadata or {}),
            created_at=now,
            last_accessed_at=now,
        )
        self._memories[entry.id] = entry
        self._fingerprints[fingerprint] = entry.id

        if tier is MemoryTier.SEMANTIC:
            await self._ensure_mem0()
            stored_external = False
            if self._mem0.is_available:
                try:
                    mem0_id = await self._mem0.add(
                        content,
                        metadata=entry.metadata,
                        user_id=self._user_id,
                    )
                    if mem0_id:
                        entry.metadata["mem0_id"] = mem0_id
                        stored_external = True
                except Exception as exc:
                    logger.warning("memory_mem0_store_failed", error=str(exc))
            if not stored_external:
                await self._store_vector(entry)

        logger.info("memory_stored", memory_id=entry.id, tier=tier.value)
        return entry

    async def _store_vector(self, entry: MemoryEntry) -> None:
        meta = dict(entry.metadata)
        meta["tier"] = entry.tier.value
        await vector_memory.add(
            self._VECTOR_COLLECTION,
            entry.id,
            entry.content,
            metadata=meta,
        )
        logger.info("memory_vector_fallback", memory_id=entry.id)

    async def _recall_semantic(self, query: str, limit: int) -> list[MemoryEntry]:
        await self._ensure_mem0()
        if self._mem0.is_available:
            try:
                raw = await self._mem0.search(query, limit=limit, user_id=self._user_id)
            except Exception as exc:
                logger.warning("memory_mem0_search_failed", error=str(exc))
                raw = []
            return [entry for item in raw if (entry := self._from_mem0_result(item)) is not None]
        try:
            hits = await vector_memory.search(self._VECTOR_COLLECTION, query, top_k=limit)
        except Exception as exc:
            logger.warning("vector_recall_failed", error=str(exc))
            return []
        results: list[MemoryEntry] = []
        for hit in hits:
            meta = hit.get("metadata") or {}
            try:
                tier = MemoryTier(meta.get("tier", MemoryTier.SEMANTIC.value))
            except ValueError:
                tier = MemoryTier.SEMANTIC
            results.append(
                MemoryEntry(
                    id=hit["id"],
                    content=hit["text"],
                    tier=tier,
                    score=self._clamp_score(hit.get("score", 0.5)),
                    metadata=meta,
                    created_at=datetime.now(UTC),
                    last_accessed_at=datetime.now(UTC),
                )
            )
        return results

    async def recall(
        self,
        query: str,
        tier: MemoryTier | None = None,
        limit: int = 5,
    ) -> list[MemoryEntry]:
        candidates: list[MemoryEntry] = []
        if tier is None or tier is MemoryTier.SEMANTIC:
            candidates.extend(await self._recall_semantic(query, limit))

        now = datetime.now(UTC)
        for entry in self._memories.values():
            if tier is not None and entry.tier is not tier:
                continue
            entry.last_accessed_at = now
            candidates.append(
                MemoryEntry(
                    id=entry.id,
                    content=entry.content,
                    tier=entry.tier,
                    score=entry.score * self._similarity(query, entry.content),
                    metadata=dict(entry.metadata),
                    created_at=entry.created_at,
                    last_accessed_at=now,
                )
            )

        ranked: list[MemoryEntry] = []
        seen: set[str] = set()
        for entry in sorted(candidates, key=lambda e: e.score, reverse=True):
            key = self._fingerprint(entry.content)
            if key in seen:
                continue
            seen.add(key)
            ranked.append(entry)
            if len(ranked) >= limit:
                break

        logger.info(
            "memory_recalled",
            query=query,
            tier=tier.value if tier else "all",
            results=len(ranked),
        )
        return ranked

    async def consolidate(self, threshold: float = 0.9) -> int:
        entries = list(self._memories.values())
        merged = 0
        consumed: set[str] = set()

        for i, primary in enumerate(entries):
            if primary.id in consumed or primary.id not in self._memories:
                continue
            for secondary in entries[i + 1:]:
                if secondary.id in consumed or secondary.id not in self._memories:
                    continue
                if primary.tier is not secondary.tier:
                    continue
                similarity = self._similarity(primary.content, secondary.content)
                if similarity < threshold:
                    continue
                if primary.score < threshold or secondary.score < threshold:
                    continue
                merged_ids = primary.metadata.setdefault("merged_ids", [])
                merged_ids.append(secondary.id)
                primary.metadata["merged_count"] = primary.metadata.get("merged_count", 0) + 1
                primary.score = max(primary.score, secondary.score)
                self._memories.pop(secondary.id, None)
                self._fingerprints.pop(self._fingerprint(secondary.content), None)
                consumed.add(secondary.id)
                merged += 1

        if merged:
            logger.info("memory_consolidated", merged=merged, threshold=threshold)
        return merged

    async def forget(self, memory_id: str) -> bool:
        entry = self._memories.pop(memory_id, None)
        if entry is None:
            logger.info("memory_forget_missing", memory_id=memory_id)
            return False
        self._fingerprints.pop(self._fingerprint(entry.content), None)
        if entry.tier is MemoryTier.SEMANTIC:
            mem0_id = entry.metadata.get("mem0_id")
            if mem0_id:
                try:
                    await self._mem0.delete(mem0_id)
                except Exception as exc:
                    logger.warning("memory_mem0_delete_failed", error=str(exc))
        logger.info("memory_forgotten", memory_id=memory_id)
        return True

    async def stats(self) -> dict[str, Any]:
        counts = {tier.value: 0 for tier in MemoryTier}
        for entry in self._memories.values():
            counts[entry.tier.value] += 1
        return {
            "total": len(self._memories),
            "by_tier": counts,
            "mem0_available": self._mem0.is_available,
        }


_service: UnifiedMemoryService | None = None
_service_lock = asyncio.Lock()


async def get_unified_memory() -> UnifiedMemoryService:
    global _service
    if _service is None:
        async with _service_lock:
            if _service is None:
                _service = UnifiedMemoryService()
    return _service

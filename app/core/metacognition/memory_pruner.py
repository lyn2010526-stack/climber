"""Long-Term Memory Pruner — memory evolution and consolidation.

Merges redundant memories, forgets low-value old experiences,
extracts general patterns. Prevents unbounded knowledge base growth.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryEntry:
    id: str
    content: str
    importance: float  # 0.0-1.0
    created_at: float
    last_accessed: float
    access_count: int = 0
    tags: list[str] = field(default_factory=list)

    @property
    def age_days(self) -> float:
        return (time.time() - self.created_at) / 86400

    @property
    def decayed_importance(self) -> float:
        """Importance decays over time but is boosted by access."""
        age_factor = max(0.1, 1 - self.age_days / 30)  # Decay over 30 days
        access_boost = min(0.3, self.access_count * 0.05)
        return min(1.0, self.importance * age_factor + access_boost)


@dataclass
class PruneResult:
    original_count: int
    pruned_count: int
    merged_count: int
    removed_ids: list[str]
    merged_groups: list[list[str]]


class LongTermMemoryPruner:
    """Consolidate and prune long-term memory."""

    def __init__(
        self,
        storage_path: str = "data/long_term_memory.json",
        max_entries: int = 1000,
    ):
        self._storage_path = storage_path
        self._max_entries = max_entries
        self._memories: dict[str, MemoryEntry] = {}
        self._load()

    def add_memory(
        self,
        memory_id: str,
        content: str,
        importance: float = 0.5,
        tags: list[str] | None = None,
    ) -> MemoryEntry:
        entry = MemoryEntry(
            id=memory_id,
            content=content,
            importance=importance,
            created_at=time.time(),
            last_accessed=time.time(),
            tags=tags or [],
        )
        self._memories[memory_id] = entry
        return entry

    def access_memory(self, memory_id: str) -> MemoryEntry | None:
        entry = self._memories.get(memory_id)
        if entry:
            entry.access_count += 1
            entry.last_accessed = time.time()
        return entry

    def prune(self, force: bool = False) -> PruneResult:
        """Run full pruning pipeline."""
        original_count = len(self._memories)
        removed_ids: list[str] = []
        merged_groups: list[list[str]] = []

        # Step 1: Remove low-value old memories
        if force or len(self._memories) > self._max_entries:
            removed_ids = self._remove_low_value()

        # Step 2: Merge similar memories
        merged_groups = self._merge_similar()
        for group in merged_groups:
            # Keep first, remove rest
            for mid in group[1:]:
                if mid in self._memories:
                    del self._memories[mid]
                    removed_ids.append(mid)

        # Step 3: Extract patterns (just log for now)
        self._extract_patterns()

        self._save()

        return PruneResult(
            original_count=original_count,
            pruned_count=len(self._memories),
            merged_count=len(merged_groups),
            removed_ids=removed_ids,
            merged_groups=merged_groups,
        )

    def _remove_low_value(self) -> list[str]:
        """Remove memories with lowest decayed importance."""
        removed: list[str] = []
        target_size = int(self._max_entries * 0.8)

        if len(self._memories) <= target_size:
            return removed

        scored = [
            (entry.decayed_importance, mid)
            for mid, entry in self._memories.items()
        ]
        scored.sort()

        to_remove = len(self._memories) - target_size
        for _, mid in scored[:to_remove]:
            del self._memories[mid]
            removed.append(mid)

        return removed

    def _merge_similar(self) -> list[list[str]]:
        """Find and merge similar memories."""
        groups: list[list[str]] = []
        processed = set()

        memories = list(self._memories.values())
        for i, mem in enumerate(memories):
            if mem.id in processed:
                continue
            group = [mem.id]
            processed.add(mem.id)

            for j in range(i + 1, len(memories)):
                other = memories[j]
                if other.id in processed:
                    continue
                similarity = self._compute_similarity(mem, other)
                if similarity > 0.7:
                    group.append(other.id)
                    processed.add(other.id)

            if len(group) > 1:
                groups.append(group)
                # Merge content into first entry
                merged_content = " | ".join(
                    self._memories[mid].content for mid in group
                    if mid in self._memories
                )
                self._memories[group[0]].content = f"[Merged] {merged_content[:500]}"

        return groups

    def _compute_similarity(self, a: MemoryEntry, b: MemoryEntry) -> float:
        """Simple word overlap similarity."""
        words_a = set(a.content.lower().split())
        words_b = set(b.content.lower().split())
        if not words_a or not words_b:
            return 0.0
        return len(words_a & words_b) / len(words_a | words_b)

    def _extract_patterns(self) -> list[str]:
        """Extract recurring patterns from memories."""
        # Simple pattern: find common tags
        tag_counts: dict[str, int] = {}
        for entry in self._memories.values():
            for tag in entry.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        patterns = [
            f"Pattern: '{tag}' appears {count} times"
            for tag, count in tag_counts.items()
            if count >= 3
        ]
        return patterns

    def get_stats(self) -> dict[str, Any]:
        if not self._memories:
            return {"count": 0, "avg_importance": 0, "avg_age_days": 0}

        importances = [m.decayed_importance for m in self._memories.values()]
        ages = [m.age_days for m in self._memories.values()]

        return {
            "count": len(self._memories),
            "avg_importance": sum(importances) / len(importances),
            "avg_age_days": sum(ages) / len(ages),
            "max_entries": self._max_entries,
        }

    def search(self, query: str, limit: int = 5) -> list[MemoryEntry]:
        """Search memories by relevance."""
        query_words = set(query.lower().split())
        scored = []
        for entry in self._memories.values():
            entry_words = set(entry.content.lower().split())
            if not entry_words:
                continue
            overlap = len(query_words & entry_words) / max(len(query_words), 1)
            score = overlap * entry.decayed_importance
            scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:limit]]

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._storage_path), exist_ok=True)
        data = {
            mid: {
                "id": m.id,
                "content": m.content,
                "importance": m.importance,
                "created_at": m.created_at,
                "last_accessed": m.last_accessed,
                "access_count": m.access_count,
                "tags": m.tags,
            }
            for mid, m in self._memories.items()
        }
        with open(self._storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self) -> None:
        if not os.path.exists(self._storage_path):
            return
        try:
            with open(self._storage_path) as f:
                data = json.load(f)
            for mid, m in data.items():
                self._memories[mid] = MemoryEntry(
                    id=m["id"],
                    content=m["content"],
                    importance=m.get("importance", 0.5),
                    created_at=m.get("created_at", time.time()),
                    last_accessed=m.get("last_accessed", time.time()),
                    access_count=m.get("access_count", 0),
                    tags=m.get("tags", []),
                )
        except (json.JSONDecodeError, KeyError):
            pass

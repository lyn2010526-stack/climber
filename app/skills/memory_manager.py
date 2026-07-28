"""Persistent File-Backed Memory Manager.

Stores agent memories, facts, and knowledge on disk for persistence across sessions.
Supports: facts, preferences, project context, conversation summaries, and RAG documents.
"""

from __future__ import annotations

import json
import os
import re
import time
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class MemoryType(str, Enum):
    FACT = "fact"                  # Short factual statements
    PREFERENCE = "preference"      # User preferences
    PROJECT = "project"            # Project-specific context
    CONVERSATION = "conversation"  # Conversation summaries
    SKILL = "skill"                # Learned skill patterns
    ERROR = "error"                # Lessons from errors
    DECISION = "decision"          # Architecture/tech decisions


class MemoryEntry(BaseModel):
    """A single memory entry."""
    id: str
    type: MemoryType
    content: str
    tags: list[str] = Field(default_factory=list)
    importance: float = 1.0        # 0.0 - 1.0
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    access_count: int = 0
    source: str = ""               # Where this memory came from


class PersistentMemoryManager:
    """File-backed persistent memory for agents.

    Stores memories as JSONL files organized by type.
    Supports CRUD, search, decay, and consolidation.
    """

    def __init__(self, base_path: str = "/workspace/.agent_memory"):
        self.base_path = base_path
        self._cache: dict[str, MemoryEntry] = {}
        self._ensure_dirs()
        self._load_all()

    def _ensure_dirs(self):
        os.makedirs(self.base_path, exist_ok=True)
        for mt in MemoryType:
            os.makedirs(os.path.join(self.base_path, mt.value), exist_ok=True)

    def _entry_path(self, entry_id: str) -> str:
        """Get the file path for a memory entry."""
        # Use first 2 chars as subdirectory for distribution
        subdir = entry_id[:2]
        return os.path.join(self.base_path, subdir, f"{entry_id}.json")

    def _load_all(self):
        """Load all memories from disk."""
        self._cache = {}
        for root, _, files in os.walk(self.base_path):
            for fname in files:
                if fname.endswith(".json"):
                    try:
                        with open(os.path.join(root, fname), "r") as f:
                            data = json.load(f)
                        entry = MemoryEntry(**data)
                        self._cache[entry.id] = entry
                    except (json.JSONDecodeError, KeyError):
                        continue

    def _save_entry(self, entry: MemoryEntry):
        """Persist a single entry to disk."""
        subdir = os.path.join(self.base_path, entry.id[:2])
        os.makedirs(subdir, exist_ok=True)
        path = os.path.join(subdir, f"{entry.id}.json")
        with open(path, "w") as f:
            f.write(entry.model_dump_json())

    def _delete_entry(self, entry_id: str):
        """Delete a single entry from disk."""
        path = self._entry_path(entry_id)
        if os.path.exists(path):
            os.remove(path)

    # ── Public API ──

    def store(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.FACT,
        tags: list[str] | None = None,
        importance: float = 1.0,
        source: str = "",
    ) -> MemoryEntry:
        """Store a new memory."""
        entry_id = f"mem-{int(time.time() * 1000)}-{len(self._cache)}"
        entry = MemoryEntry(
            id=entry_id,
            type=memory_type,
            content=content,
            tags=tags or [],
            importance=importance,
            source=source,
        )
        self._cache[entry_id] = entry
        self._save_entry(entry)
        return entry

    def recall(
        self,
        query: str = "",
        memory_type: MemoryType | None = None,
        tags: list[str] | None = None,
        limit: int = 10,
        min_importance: float = 0.0,
    ) -> list[MemoryEntry]:
        """Search and recall relevant memories."""
        results = []

        for entry in self._cache.values():
            # Filter by type
            if memory_type and entry.type != memory_type:
                continue

            # Filter by importance
            if entry.importance < min_importance:
                continue

            # Filter by tags
            if tags and not any(t in entry.tags for t in tags):
                continue

            # Score relevance
            score = self._score_relevance(entry, query)
            if query and score == 0:
                continue

            results.append((score, entry))

        # Sort by score (desc), then importance, then recency
        results.sort(key=lambda x: (-x[0], -x[1].importance, -x[1].updated_at))

        # Update access count
        for _, entry in results[:limit]:
            entry.access_count += 1
            self._save_entry(entry)

        return [entry for _, entry in results[:limit]]

    def _score_relevance(self, entry: MemoryEntry, query: str) -> float:
        """Score how relevant a memory is to a query."""
        if not query:
            return entry.importance

        query_lower = query.lower()
        content_lower = entry.content.lower()

        # Exact match bonus
        if query_lower in content_lower:
            return 2.0 + entry.importance

        # Tag match
        tag_matches = sum(1 for t in entry.tags if query_lower in t.lower())
        if tag_matches > 0:
            return 1.5 + entry.importance

        # Word overlap
        query_words = set(re.findall(r"\b\w+\b", query_lower))
        content_words = set(re.findall(r"\b\w+\b", content_lower))
        overlap = len(query_words & content_words)
        if overlap > 0:
            return (overlap / max(len(query_words), 1)) + entry.importance

        return 0.0

    def update(self, entry_id: str, **kwargs) -> MemoryEntry | None:
        """Update an existing memory."""
        entry = self._cache.get(entry_id)
        if not entry:
            return None

        for key, value in kwargs.items():
            if hasattr(entry, key):
                setattr(entry, key, value)

        entry.updated_at = time.time()
        self._save_entry(entry)
        return entry

    def forget(self, entry_id: str) -> bool:
        """Remove a memory."""
        if entry_id in self._cache:
            self._delete_entry(entry_id)
            del self._cache[entry_id]
            return True
        return False

    def consolidate(self) -> dict[str, int]:
        """Clean up: remove low-importance, rarely accessed old memories."""
        removed = {"low_importance": 0, "old_unused": 0}
        cutoff = time.time() - (30 * 24 * 3600)  # 30 days

        to_remove = []
        for entry_id, entry in self._cache.items():
            if entry.importance < 0.2 and entry.access_count == 0:
                to_remove.append(entry_id)
                removed["low_importance"] += 1
            elif entry.updated_at < cutoff and entry.access_count < 2:
                to_remove.append(entry_id)
                removed["old_unused"] += 1

        for entry_id in to_remove:
            self.forget(entry_id)

        return removed

    def get_project_context(self, project: str) -> list[MemoryEntry]:
        """Get all memories related to a project."""
        return self.recall(query=project, memory_type=MemoryType.PROJECT, limit=20)

    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        type_counts: dict[str, int] = {}
        for entry in self._cache.values():
            type_counts[entry.type.value] = type_counts.get(entry.type.value, 0) + 1

        return {
            "total_memories": len(self._cache),
            "by_type": type_counts,
            "storage_path": self.base_path,
        }

    def export_all(self) -> list[dict[str, Any]]:
        """Export all memories as a list of dicts."""
        return [entry.model_dump() for entry in self._cache.values()]


# Global singleton
persistent_memory = PersistentMemoryManager()

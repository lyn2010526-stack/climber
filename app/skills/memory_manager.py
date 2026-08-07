"""Memory manager for skills — provides persistent memory storage."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class MemoryType(StrEnum):
    FACT = "fact"
    PREFERENCE = "preference"
    TASK = "task"
    CONTEXT = "context"
    EVENT = "event"


@dataclass
class MemoryEntry:
    id: str
    content: str
    memory_type: MemoryType
    source: str
    created_at: datetime
    metadata: dict[str, Any]


class PersistentMemory:
    """Simple persistent memory store."""

    def __init__(self):
        self._cache: list[MemoryEntry] = []

    def store(self, content: str, memory_type: MemoryType = MemoryType.FACT, source: str = "system", **kwargs) -> MemoryEntry:
        entry = MemoryEntry(
            id=str(uuid.uuid4())[:12],
            content=content,
            memory_type=memory_type,
            source=source,
            created_at=datetime.now(UTC),
            metadata=kwargs,
        )
        self._cache.append(entry)
        return entry

    def recall(self, query: str = "", limit: int = 10, memory_type: MemoryType | None = None) -> list[MemoryEntry]:
        results = self._cache
        if memory_type:
            results = [e for e in results if e.memory_type == memory_type]
        if query:
            results = [e for e in results if query.lower() in e.content.lower()]
        return results[-limit:]

    def get_stats(self) -> dict[str, int]:
        stats: dict[str, int] = {}
        for mt in MemoryType:
            stats[mt.value] = len([e for e in self._cache if e.memory_type == mt])
        stats["total"] = len(self._cache)
        return stats

    def clear(self) -> int:
        count = len(self._cache)
        self._cache.clear()
        return count


persistent_memory = PersistentMemory()

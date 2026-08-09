"""Memory Provider abstraction.

"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class MemoryRecord:
    id: str
    text: str
    embedding: list[float] | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime | None = None
    access_count: int = 0
    last_accessed: datetime | None = None


class MemoryProvider(ABC):
    """Abstract base class for memory backends."""

    @abstractmethod
    async def add(self, record: MemoryRecord) -> str:
        """Add a memory record. Returns the record ID."""
        ...

    @abstractmethod
    async def get(self, record_id: str) -> MemoryRecord | None:
        """Get a memory record by ID."""
        ...

    @abstractmethod
    async def search(self, query: str, top_k: int = 5, tags: list[str] | None = None) -> list[MemoryRecord]:
        """Search memories by semantic similarity."""
        ...

    @abstractmethod
    async def delete(self, record_id: str) -> bool:
        """Delete a memory record."""
        ...

    @abstractmethod
    async def update_access(self, record_id: str) -> None:
        """Update access count and last_accessed timestamp."""
        ...

    @abstractmethod
    async def list_tags(self) -> list[str]:
        """List all unique tags."""
        ...

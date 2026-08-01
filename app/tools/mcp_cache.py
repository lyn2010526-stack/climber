"""Tool result caching with TTL support."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from typing import Any

import structlog

logger = structlog.get_logger()


class CacheEntry:
    """A single cache entry with TTL."""

    def __init__(self, value: Any, ttl_ms: int | None = None) -> None:
        self.value = value
        self.created_at = time.monotonic()
        self.ttl_ms = ttl_ms

    @property
    def is_expired(self) -> bool:
        if self.ttl_ms is None:
            return False
        elapsed = (time.monotonic() - self.created_at) * 1000
        return elapsed > self.ttl_ms


class ToolResultCache:
    """Cache tool results with configurable TTL per tool."""

    def __init__(self, default_ttl_ms: int | None = None, max_size: int = 1000) -> None:
        self._cache: dict[str, CacheEntry] = {}
        self._tool_index: dict[str, set[str]] = {}
        self._default_ttl_ms = default_ttl_ms
        self._max_size = max_size
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _make_key(tool_name: str, arguments: dict[str, Any]) -> str:
        """Create a deterministic cache key."""
        arg_str = json.dumps(arguments, sort_keys=True, default=str)
        raw = f"{tool_name}:{arg_str}"
        return hashlib.sha256(raw.encode()).hexdigest()

    async def get(self, tool_name: str, arguments: dict[str, Any]) -> Any | None:
        """Retrieve cached result if available and not expired."""
        key = self._make_key(tool_name, arguments)
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.is_expired:
                del self._cache[key]
                self._misses += 1
                return None
            self._hits += 1
            return entry.value

    async def set(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        result: Any,
        ttl_ms: int | None = None,
    ) -> None:
        """Store a result in the cache."""
        key = self._make_key(tool_name, arguments)
        ttl = ttl_ms if ttl_ms is not None else self._default_ttl_ms
        async with self._lock:
            if len(self._cache) >= self._max_size:
                self._evict_oldest()
            self._cache[key] = CacheEntry(result, ttl)
            if tool_name not in self._tool_index:
                self._tool_index[tool_name] = set()
            self._tool_index[tool_name].add(key)

    async def invalidate(self, tool_name: str) -> int:
        """Invalidate all cached entries for a tool."""
        async with self._lock:
            keys = self._tool_index.pop(tool_name, set())
            for k in keys:
                self._cache.pop(k, None)
            return len(keys)

    async def clear(self) -> None:
        """Clear all cached entries."""
        async with self._lock:
            self._cache.clear()
            self._tool_index.clear()

    def _evict_oldest(self) -> None:
        """Evict oldest entries when cache is full."""
        if not self._cache:
            return
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].created_at,
        )
        to_remove = sorted_entries[: len(sorted_entries) // 4]
        for k, _ in to_remove:
            del self._cache[k]

    @property
    def stats(self) -> dict[str, int]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": (
                self._hits / (self._hits + self._misses) * 100
                if (self._hits + self._misses) > 0
                else 0
            ),
        }

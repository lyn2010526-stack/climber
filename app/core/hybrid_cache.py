"""Unified cache layer: Redis-backed when available, process-local fallback.

Provides a consistent async interface for TTL caching across the application.
If Redis is connected, all operations use Redis for cross-worker sharing.
If Redis is unavailable, falls back to in-process TTL caches transparently.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import structlog

logger = structlog.get_logger()


class _LocalTTLCache:
    """Process-scoped TTL cache for a single value."""

    def __init__(self, ttl: float) -> None:
        self._ttl = ttl
        self._data: Any = None
        self._ts: float = 0.0

    def get(self) -> Any | None:
        if self._data is not None and time.monotonic() - self._ts < self._ttl:
            return self._data
        return None

    def set(self, value: Any) -> None:
        self._data = value
        self._ts = time.monotonic()


class _LocalKeyedCache:
    """Per-key TTL cache for multiple values keyed by string id."""

    def __init__(self, ttl: float) -> None:
        self._ttl = ttl
        self._data: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._data.get(key)
        if entry is not None:
            value, ts = entry
            if time.monotonic() - ts < self._ttl:
                return value
            del self._data[key]
        return None

    def set(self, key: str, value: Any) -> None:
        self._data[key] = (value, time.monotonic())

    def invalidate(self, key: str) -> None:
        self._data.pop(key, None)

    def invalidate_all(self) -> None:
        self._data.clear()


class HybridCache:
    """Cache that uses Redis when available, falling back to local memory.

    - ``get_scalar`` / ``set_scalar``: cache a single value (list cache)
    - ``get_keyed`` / ``set_keyed``: cache per-key values (detail cache)
    """

    def __init__(self, name: str, ttl: float) -> None:
        self._name = name
        self._ttl = ttl
        self._local_scalar = _LocalTTLCache(ttl=ttl)
        self._local_keyed = _LocalKeyedCache(ttl=ttl)
        self._redis = None

    async def _ensure_redis(self):
        if self._redis is None:
            try:
                from app.storage.cache import get_redis
                self._redis = await get_redis()
            except Exception:
                self._redis = None
        return self._redis

    def _redis_key(self, suffix: str = "") -> str:
        return f"cache:{self._name}:{suffix}" if suffix else f"cache:{self._name}"

    # ── Scalar operations (for list endpoints) ──────────────────────────────

    async def get_scalar(self) -> Any | None:
        redis = await self._ensure_redis()
        if redis:
            try:
                data = await redis.get(self._redis_key())
                if data:
                    return json.loads(data)
            except Exception:
                logger.debug("hybrid_cache.redis_get_failed", cache=self._name, exc_info=True)
        return self._local_scalar.get()

    async def set_scalar(self, value: Any) -> None:
        redis = await self._ensure_redis()
        if redis:
            try:
                await redis.set(self._redis_key(), json.dumps(value, default=str), ex=int(self._ttl))
            except Exception:
                logger.debug("hybrid_cache.redis_set_failed", cache=self._name, exc_info=True)
        self._local_scalar.set(value)

    async def invalidate_scalar(self) -> None:
        redis = await self._ensure_redis()
        if redis:
            try:
                await redis.delete(self._redis_key())
            except Exception:
                pass
        self._local_scalar.set(None)

    # ── Keyed operations (for detail endpoints) ────────────────────────────

    async def get_keyed(self, key: str) -> Any | None:
        redis = await self._ensure_redis()
        if redis:
            try:
                data = await redis.get(self._redis_key(key))
                if data:
                    return json.loads(data)
            except Exception:
                logger.debug("hybrid_cache.redis_get_keyed_failed", cache=self._name, key=key, exc_info=True)
        return self._local_keyed.get(key)

    async def set_keyed(self, key: str, value: Any) -> None:
        redis = await self._ensure_redis()
        if redis:
            try:
                await redis.set(self._redis_key(key), json.dumps(value, default=str), ex=int(self._ttl))
            except Exception:
                logger.debug("hybrid_cache.redis_set_keyed_failed", cache=self._name, key=key, exc_info=True)
        self._local_keyed.set(key, value)

    async def invalidate_keyed(self, key: str) -> None:
        redis = await self._ensure_redis()
        if redis:
            try:
                await redis.delete(self._redis_key(key))
            except Exception:
                pass
        self._local_keyed.invalidate(key)

    async def invalidate_all_keyed(self) -> None:
        redis = await self._ensure_redis()
        if redis:
            try:
                async for key in redis.scan_iter(f"{self._redis_key()}:*"):
                    await redis.delete(key)
            except Exception:
                pass
        self._local_keyed.invalidate_all()

"""Redis caching layer."""

from __future__ import annotations

import hashlib
import json
from functools import wraps
from typing import Any

import structlog

logger = structlog.get_logger()

_redis_client = None


async def get_redis():
    """Get or create Redis client singleton."""
    global _redis_client
    if _redis_client is None:
        import redis.asyncio as redis

        from app.config import settings
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        try:
            await _redis_client.ping()
            logger.info("Redis connected")
        except Exception:
            logger.warning("Redis unavailable, caching disabled")
            _redis_client = None
    return _redis_client


async def close_redis():
    """Close Redis connection."""
    global _redis_client
    redis_client = _redis_client
    _redis_client = None
    if not redis_client:
        return

    try:
        if hasattr(redis_client, "aclose"):
            await redis_client.aclose()
        else:
            await redis_client.close()
    except RuntimeError as exc:
        if str(exc) != "Event loop is closed":
            raise
        logger.debug("Redis client loop already closed")


class Cache:
    """Simple Redis cache wrapper."""

    def __init__(self, redis_client=None, prefix: str = "ae"):
        self._redis = redis_client
        self._prefix = prefix

    def _key(self, key: str) -> str:
        return f"{self._prefix}:{key}"

    async def get(self, key: str) -> Any | None:
        if not self._redis:
            return None
        try:
            data = await self._redis.get(self._key(key))
            if data:
                return json.loads(data)
        except Exception:
            logger.debug("storage.cache.suppressed", exc_info=True)
        return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        if not self._redis:
            return False
        cache_key = self._key(key)
        try:
            await self._redis.set(cache_key, json.dumps(value, default=str), ex=ttl)
            return True
        except Exception:
            logger.warning("storage.cache.set_failed", cache_key=cache_key, ttl=ttl, exc_info=True)
            return False

    async def delete(self, key: str) -> bool:
        if not self._redis:
            return False
        cache_key = self._key(key)
        try:
            await self._redis.delete(cache_key)
            return True
        except Exception:
            logger.warning("storage.cache.delete_failed", cache_key=cache_key, exc_info=True)
            return False

    async def increment(self, key: str, amount: int = 1) -> int:
        if not self._redis:
            return 0
        cache_key = self._key(key)
        try:
            return await self._redis.incrby(cache_key, amount)
        except Exception:
            logger.warning("storage.cache.increment_failed", cache_key=cache_key, amount=amount, exc_info=True)
            return 0

    async def expire(self, key: str, seconds: int) -> bool:
        if not self._redis:
            return False
        cache_key = self._key(key)
        try:
            return await self._redis.expire(cache_key, seconds)
        except Exception:
            logger.warning("storage.cache.expire_failed", cache_key=cache_key, seconds=seconds, exc_info=True)
            return False


def cached(ttl: int = 300, key_prefix: str = "cache"):
    """Decorator for caching async function results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = Cache(await get_redis())
            cache_key = f"{key_prefix}:{func.__name__}:{hashlib.md5(str(args).encode()).hexdigest()[:8]}:{hashlib.md5(str(sorted(kwargs.items())).encode()).hexdigest()[:8]}"  # noqa: S324 - cache-key hash, non-crypto
            result = await cache.get(cache_key)
            if result is not None:
                return result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator

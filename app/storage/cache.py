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
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


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
            pass
        return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        if not self._redis:
            return False
        try:
            await self._redis.set(self._key(key), json.dumps(value, default=str), ex=ttl)
            return True
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        if not self._redis:
            return False
        try:
            await self._redis.delete(self._key(key))
            return True
        except Exception:
            return False

    async def increment(self, key: str, amount: int = 1) -> int:
        if not self._redis:
            return 0
        try:
            return await self._redis.incrby(self._key(key), amount)
        except Exception:
            return 0

    async def expire(self, key: str, seconds: int) -> bool:
        if not self._redis:
            return False
        try:
            return await self._redis.expire(self._key(key), seconds)
        except Exception:
            return False


def cached(ttl: int = 300, key_prefix: str = "cache"):
    """Decorator for caching async function results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = Cache(await get_redis())
            cache_key = f"{key_prefix}:{func.__name__}:{hashlib.md5(str(args).encode()).hexdigest()[:8]}:{hashlib.md5(str(sorted(kwargs.items())).encode()).hexdigest()[:8]}"
            result = await cache.get(cache_key)
            if result is not None:
                return result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator

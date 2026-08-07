"""Cache: service_worker."""

from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass
class ServiceWorkerCacheEntry:
    """Cache entry."""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    hits: int = 0


@dataclass
class ServiceWorkerCacheConfig:
    """Cache config."""
    max_size: int = 1000
    default_ttl: int = 3600
    cleanup_interval: int = 300


class ServiceWorkerCache:
    """Cache implementation."""

    def __init__(self, config: ServiceWorkerCacheConfig | None = None):
        self.config = config or ServiceWorkerCacheConfig()
        self._store: dict[str, ServiceWorkerCacheEntry] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any:
        """Get value."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.expires_at and datetime.utcnow() > entry.expires_at:
                del self._store[key]
                self._misses += 1
                return None
            entry.hits += 1
            self._hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value."""
        with self._lock:
            if len(self._store) >= self.config.max_size:
                self._evict()
            expires = None
            if ttl is not None:
                expires = datetime.utcnow() + timedelta(seconds=ttl)
            elif self.config.default_ttl > 0:
                expires = datetime.utcnow() + timedelta(seconds=self.config.default_ttl)
            self._store[key] = ServiceWorkerCacheEntry(
                key=key, value=value, expires_at=expires)

    def delete(self, key: str) -> bool:
        """Delete value."""
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def clear(self) -> None:
        """Clear cache."""
        with self._lock:
            self._store.clear()

    def has(self, key: str) -> bool:
        """Check existence."""
        entry = self._store.get(key)
        if entry is None:
            return False
        return not (entry.expires_at and datetime.utcnow() > entry.expires_at)

    def _evict(self) -> None:
        """Evict entry."""
        if not self._store:
            return
        min_key = min(self._store, key=lambda k: self._store[k].hits)
        del self._store[min_key]

    def stats(self) -> dict:
        """Get stats."""
        return {
            'size': len(self._store),
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': self._hits / (self._hits + self._misses) if (self._hits + self._misses) > 0 else 0
        }


def service_worker_cache_key(*args, **kwargs) -> str:
    """Generate cache key."""
    key_data = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True, default=str)
    return hashlib.md5(key_data.encode()).hexdigest()


def service_worker_cached(cache: ServiceWorkerCache, ttl: int | None = None):
    """Cache decorator."""
    def decorator(fn: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            key = service_worker_cache_key(fn.__name__, *args, **kwargs)
            cached_value = cache.get(key)
            if cached_value is not None:
                return cached_value
            result = fn(*args, **kwargs)
            cache.set(key, result, ttl=ttl)
            return result
        return wrapper
    return decorator

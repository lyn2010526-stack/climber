"""Shared infrastructure for the generic API domain modules.

Holds Prometheus metric objects (registered once), background task helper,
TTL caches, hybrid caches, and common request helpers so that each domain
module can import them without re-registering duplicate metric names.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import structlog
from fastapi import Request
from prometheus_client import Counter, Histogram

from app.core.hybrid_cache import HybridCache

logger = structlog.get_logger()

_background_tasks: set[asyncio.Task] = set()

# ─── Prometheus Metrics ────────────────────────────────────────────────────────

# Cache metrics
_cache_hits_total = Counter('cache_hits_total', 'Total cache hits', ['cache_type'])
_cache_misses_total = Counter('cache_misses_total', 'Total cache misses', ['cache_type'])
_cache_ttl_seconds = Histogram('cache_ttl_seconds', 'Cache TTL distribution', ['cache_type'])

# DB query metrics
_db_query_duration_seconds = Histogram('db_query_duration_seconds', 'Database query duration', ['endpoint', 'operation'])
_db_queries_total = Counter('db_queries_total', 'Total database queries', ['endpoint', 'operation'])

# Agent metrics
_agents_created_total = Counter('agents_created_total', 'Total agents created')
_agents_deleted_total = Counter('agents_deleted_total', 'Total agents deleted')

# Task metrics
_tasks_created_total = Counter('tasks_created_total', 'Total tasks created')
_tasks_completed_total = Counter('tasks_completed_total', 'Total tasks completed')

# Session metrics
_sessions_created_total = Counter('sessions_created_total', 'Total sessions created')
_sessions_deleted_total = Counter('sessions_deleted_total', 'Total sessions deleted')


def _spawn(coro: Any) -> None:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


# ─── TTL Cache ──────────────────────────────────────────────────────────────

# Legacy sync caches (kept for backward compat with existing invalidation calls)
class _TTLCache:
    """Simple process-scoped TTL cache."""

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


class _KeyedCache:
    """Per-key TTL cache (dict keyed by string id)."""

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


_agents_cache = _TTLCache(ttl=120.0)   # 2 min
_models_cache = _TTLCache(ttl=300.0)  # 5 min
_agent_detail_cache = _KeyedCache(ttl=60.0)  # 60s per agent

# Hybrid caches (Redis-backed when available, local fallback)
_hybrid_agents = HybridCache(name="agents_list", ttl=120.0)
_hybrid_models = HybridCache(name="models_list", ttl=300.0)
_hybrid_agent_detail = HybridCache(name="agent_detail", ttl=60.0)

DEFAULT_USER = "default-user"


async def _payload(request: Request) -> dict[str, Any]:
    """Read a JSON body tolerantly: flat object or {"data": {...}} envelope."""
    try:
        raw = await request.json()
    except Exception:
        return {}
    if not isinstance(raw, dict):
        return {}
    inner = raw.get("data")
    if isinstance(inner, dict):
        return inner
    return raw

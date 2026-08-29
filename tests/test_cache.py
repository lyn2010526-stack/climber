"""Tests for the Redis cache lifecycle."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.storage import cache


@pytest.fixture(autouse=True)
def reset_redis_client():
    cache._redis_client = None
    yield
    cache._redis_client = None


@pytest.mark.asyncio
async def test_close_redis_prefers_aclose():
    redis_client = MagicMock()
    redis_client.aclose = AsyncMock()
    redis_client.close = AsyncMock()
    cache._redis_client = redis_client

    await cache.close_redis()

    redis_client.aclose.assert_awaited_once_with()
    redis_client.close.assert_not_called()
    assert cache._redis_client is None


@pytest.mark.asyncio
async def test_close_redis_falls_back_to_legacy_close():
    redis_client = MagicMock(spec=["close"])
    redis_client.close = AsyncMock()
    cache._redis_client = redis_client

    await cache.close_redis()

    redis_client.close.assert_awaited_once_with()
    assert cache._redis_client is None


@pytest.mark.asyncio
async def test_close_redis_discards_client_bound_to_closed_event_loop():
    redis_client = MagicMock()
    redis_client.aclose = AsyncMock(side_effect=RuntimeError("Event loop is closed"))
    cache._redis_client = redis_client

    await cache.close_redis()

    redis_client.aclose.assert_awaited_once_with()
    assert cache._redis_client is None

"""Tests for Redis cache layer."""

from __future__ import annotations

import json
import unittest.mock as mock

import pytest

from app.storage.cache import Cache, cached, close_redis


class TestCacheInit:
    """Tests for Cache initialization."""

    def test_default_prefix(self):
        cache = Cache()
        assert cache._prefix == "ae"
        assert cache._redis is None

    def test_custom_prefix(self):
        cache = Cache(prefix="custom")
        assert cache._prefix == "custom"

    def test_with_redis_client(self):
        mock_redis = mock.MagicMock()
        cache = Cache(redis_client=mock_redis)
        assert cache._redis is mock_redis


class TestCacheKey:
    """Tests for _key method."""

    def test_key_format(self):
        cache = Cache(prefix="test")
        assert cache._key("mykey") == "test:mykey"

    def test_key_with_empty_prefix(self):
        cache = Cache(prefix="")
        assert cache._key("mykey") == ":mykey"


class TestCacheGet:
    """Tests for Cache.get."""

    @pytest.mark.asyncio
    async def test_get_no_redis(self):
        cache = Cache()
        result = await cache.get("any-key")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_success(self):
        mock_redis = mock.MagicMock()
        mock_redis.get = mock.AsyncMock(return_value=json.dumps({"data": "value"}))
        cache = Cache(redis_client=mock_redis)
        result = await cache.get("test-key")
        assert result == {"data": "value"}
        mock_redis.get.assert_called_once_with("ae:test-key")

    @pytest.mark.asyncio
    async def test_get_missing_key(self):
        mock_redis = mock.MagicMock()
        mock_redis.get = mock.AsyncMock(return_value=None)
        cache = Cache(redis_client=mock_redis)
        result = await cache.get("missing")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_invalid_json(self):
        mock_redis = mock.MagicMock()
        mock_redis.get = mock.AsyncMock(return_value="not json")
        cache = Cache(redis_client=mock_redis)
        result = await cache.get("bad-json")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_redis_error(self):
        mock_redis = mock.MagicMock()
        mock_redis.get = mock.AsyncMock(side_effect=ConnectionError("fail"))
        cache = Cache(redis_client=mock_redis)
        result = await cache.get("error-key")
        assert result is None


class TestCacheSet:
    """Tests for Cache.set."""

    @pytest.mark.asyncio
    async def test_set_no_redis(self):
        cache = Cache()
        result = await cache.set("key", "value")
        assert result is False

    @pytest.mark.asyncio
    async def test_set_success(self):
        mock_redis = mock.MagicMock()
        mock_redis.set = mock.AsyncMock(return_value=True)
        cache = Cache(redis_client=mock_redis)
        result = await cache.set("mykey", {"data": 123}, ttl=60)
        assert result is True
        mock_redis.set.assert_called_once_with(
            "ae:mykey", json.dumps({"data": 123}, default=str), ex=60
        )

    @pytest.mark.asyncio
    async def test_set_default_ttl(self):
        mock_redis = mock.MagicMock()
        mock_redis.set = mock.AsyncMock(return_value=True)
        cache = Cache(redis_client=mock_redis)
        await cache.set("key", "val")
        mock_redis.set.assert_called_once_with("ae:key", '"val"', ex=300)

    @pytest.mark.asyncio
    async def test_set_redis_error(self):
        mock_redis = mock.MagicMock()
        mock_redis.set = mock.AsyncMock(side_effect=ConnectionError("fail"))
        cache = Cache(redis_client=mock_redis)
        result = await cache.set("key", "value")
        assert result is False


class TestCacheDelete:
    """Tests for Cache.delete."""

    @pytest.mark.asyncio
    async def test_delete_no_redis(self):
        cache = Cache()
        result = await cache.delete("key")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_success(self):
        mock_redis = mock.MagicMock()
        mock_redis.delete = mock.AsyncMock(return_value=1)
        cache = Cache(redis_client=mock_redis)
        result = await cache.delete("mykey")
        assert result is True
        mock_redis.delete.assert_called_once_with("ae:mykey")

    @pytest.mark.asyncio
    async def test_delete_redis_error(self):
        mock_redis = mock.MagicMock()
        mock_redis.delete = mock.AsyncMock(side_effect=ConnectionError("fail"))
        cache = Cache(redis_client=mock_redis)
        result = await cache.delete("key")
        assert result is False


class TestCacheIncrement:
    """Tests for Cache.increment."""

    @pytest.mark.asyncio
    async def test_increment_no_redis(self):
        cache = Cache()
        result = await cache.increment("counter")
        assert result == 0

    @pytest.mark.asyncio
    async def test_increment_success(self):
        mock_redis = mock.MagicMock()
        mock_redis.incrby = mock.AsyncMock(return_value=5)
        cache = Cache(redis_client=mock_redis)
        result = await cache.increment("counter", amount=3)
        assert result == 5
        mock_redis.incrby.assert_called_once_with("ae:counter", 3)

    @pytest.mark.asyncio
    async def test_increment_default_amount(self):
        mock_redis = mock.MagicMock()
        mock_redis.incrby = mock.AsyncMock(return_value=1)
        cache = Cache(redis_client=mock_redis)
        await cache.increment("counter")
        mock_redis.incrby.assert_called_once_with("ae:counter", 1)

    @pytest.mark.asyncio
    async def test_increment_redis_error(self):
        mock_redis = mock.MagicMock()
        mock_redis.incrby = mock.AsyncMock(side_effect=ConnectionError("fail"))
        cache = Cache(redis_client=mock_redis)
        result = await cache.increment("counter")
        assert result == 0


class TestCacheExpire:
    """Tests for Cache.expire."""

    @pytest.mark.asyncio
    async def test_expire_no_redis(self):
        cache = Cache()
        result = await cache.expire("key", 60)
        assert result is False

    @pytest.mark.asyncio
    async def test_expire_success(self):
        mock_redis = mock.MagicMock()
        mock_redis.expire = mock.AsyncMock(return_value=True)
        cache = Cache(redis_client=mock_redis)
        result = await cache.expire("mykey", 120)
        assert result is True
        mock_redis.expire.assert_called_once_with("ae:mykey", 120)

    @pytest.mark.asyncio
    async def test_expire_redis_error(self):
        mock_redis = mock.MagicMock()
        mock_redis.expire = mock.AsyncMock(side_effect=ConnectionError("fail"))
        cache = Cache(redis_client=mock_redis)
        result = await cache.expire("key", 60)
        assert result is False


class TestCachedDecorator:
    """Tests for the cached decorator."""

    @pytest.mark.asyncio
    async def test_cache_miss(self):
        mock_func = mock.AsyncMock(return_value="result")
        decorated = cached(ttl=60, key_prefix="test")(mock_func)

        with mock.patch("app.storage.cache.get_redis", new=mock.AsyncMock(return_value=None)):
            result = await decorated("arg1", kwarg="value")

        assert result == "result"
        mock_func.assert_called_once_with("arg1", kwarg="value")

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        mock_func = mock.AsyncMock(return_value="fresh")
        decorated = cached(ttl=60, key_prefix="test")(mock_func)

        mock_redis = mock.MagicMock()
        mock_cache = mock.MagicMock()
        mock_cache.get = mock.AsyncMock(return_value="cached_value")
        mock_cache.set = mock.AsyncMock()

        with mock.patch("app.storage.cache.get_redis", new=mock.AsyncMock(return_value=mock_redis)):
            with mock.patch("app.storage.cache.Cache", return_value=mock_cache):
                result = await decorated("arg1")

        assert result == "cached_value"
        mock_func.assert_not_called()


class TestRedisLifecycle:
    """Tests for get_redis and close_redis."""

    @pytest.mark.asyncio
    async def test_close_redis_no_client(self):
        import app.storage.cache as cache_mod
        cache_mod._redis_client = None
        await close_redis()

    @pytest.mark.asyncio
    async def test_close_redis_with_client(self):
        import app.storage.cache as cache_mod
        mock_client = mock.MagicMock()
        mock_client.close = mock.AsyncMock()
        cache_mod._redis_client = mock_client
        await close_redis()
        mock_client.close.assert_called_once()
        assert cache_mod._redis_client is None

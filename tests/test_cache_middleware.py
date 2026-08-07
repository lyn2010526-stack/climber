"""Tests for cache middleware."""

from unittest.mock import AsyncMock

import pytest

from app.middleware.cache_middleware import CacheConfig, CacheMiddleware, CacheStats


class TestCacheMiddleware:
    """Tests for middleware."""

    @pytest.fixture
    def middleware(self):
        app = AsyncMock()
        return CacheMiddleware(app)

    def test_init(self):
        app = AsyncMock()
        mw = CacheMiddleware(app)
        assert mw.enabled is True

    def test_disabled_middleware(self):
        app = AsyncMock()
        mw = CacheMiddleware(app, enabled=False)
        assert mw.enabled is False


class TestCacheConfig:
    """Tests for config."""

    def test_default_config(self):
        config = CacheConfig()
        assert config.enabled is True
        assert '/health' in config.excluded_paths


class TestCacheStats:
    """Tests for stats."""

    def test_record(self):
        stats = CacheStats()
        stats.record(0.1)
        stats.record(0.2)
        assert stats.total_requests == 2

    def test_get_summary(self):
        stats = CacheStats()
        stats.record(0.1)
        summary = stats.get_summary()
        assert summary['total_requests'] == 1

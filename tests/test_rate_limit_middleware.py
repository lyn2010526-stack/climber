"""Tests for rate_limit middleware."""

from unittest.mock import AsyncMock

import pytest

from app.middleware.rate_limit_middleware import RateLimitConfig, RateLimitMiddleware, RateLimitStats


class TestRateLimitMiddleware:
    """Tests for middleware."""

    @pytest.fixture
    def middleware(self):
        app = AsyncMock()
        return RateLimitMiddleware(app)

    def test_init(self):
        app = AsyncMock()
        mw = RateLimitMiddleware(app)
        assert mw.enabled is True

    def test_disabled_middleware(self):
        app = AsyncMock()
        mw = RateLimitMiddleware(app, enabled=False)
        assert mw.enabled is False


class TestRateLimitConfig:
    """Tests for config."""

    def test_default_config(self):
        config = RateLimitConfig()
        assert config.enabled is True
        assert '/health' in config.excluded_paths


class TestRateLimitStats:
    """Tests for stats."""

    def test_record(self):
        stats = RateLimitStats()
        stats.record(0.1)
        stats.record(0.2)
        assert stats.total_requests == 2

    def test_get_summary(self):
        stats = RateLimitStats()
        stats.record(0.1)
        summary = stats.get_summary()
        assert summary['total_requests'] == 1

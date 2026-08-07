"""Tests for proxy middleware."""

from unittest.mock import AsyncMock

import pytest

from app.middleware.proxy_middleware import ProxyConfig, ProxyMiddleware, ProxyStats


class TestProxyMiddleware:
    """Tests for middleware."""

    @pytest.fixture
    def middleware(self):
        app = AsyncMock()
        return ProxyMiddleware(app)

    def test_init(self):
        app = AsyncMock()
        mw = ProxyMiddleware(app)
        assert mw.enabled is True

    def test_disabled_middleware(self):
        app = AsyncMock()
        mw = ProxyMiddleware(app, enabled=False)
        assert mw.enabled is False


class TestProxyConfig:
    """Tests for config."""

    def test_default_config(self):
        config = ProxyConfig()
        assert config.enabled is True
        assert '/health' in config.excluded_paths


class TestProxyStats:
    """Tests for stats."""

    def test_record(self):
        stats = ProxyStats()
        stats.record(0.1)
        stats.record(0.2)
        assert stats.total_requests == 2

    def test_get_summary(self):
        stats = ProxyStats()
        stats.record(0.1)
        summary = stats.get_summary()
        assert summary['total_requests'] == 1

"""Tests for ip_filter middleware."""

from unittest.mock import AsyncMock

import pytest

from app.middleware.ip_filter_middleware import IpFilterConfig, IpFilterMiddleware, IpFilterStats


class TestIpFilterMiddleware:
    """Tests for middleware."""

    @pytest.fixture
    def middleware(self):
        app = AsyncMock()
        return IpFilterMiddleware(app)

    def test_init(self):
        app = AsyncMock()
        mw = IpFilterMiddleware(app)
        assert mw.enabled is True

    def test_disabled_middleware(self):
        app = AsyncMock()
        mw = IpFilterMiddleware(app, enabled=False)
        assert mw.enabled is False


class TestIpFilterConfig:
    """Tests for config."""

    def test_default_config(self):
        config = IpFilterConfig()
        assert config.enabled is True
        assert '/health' in config.excluded_paths


class TestIpFilterStats:
    """Tests for stats."""

    def test_record(self):
        stats = IpFilterStats()
        stats.record(0.1)
        stats.record(0.2)
        assert stats.total_requests == 2

    def test_get_summary(self):
        stats = IpFilterStats()
        stats.record(0.1)
        summary = stats.get_summary()
        assert summary['total_requests'] == 1

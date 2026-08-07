"""Tests for geo middleware."""

from unittest.mock import AsyncMock

import pytest

from app.middleware.geo_middleware import GeoConfig, GeoMiddleware, GeoStats


class TestGeoMiddleware:
    """Tests for middleware."""

    @pytest.fixture
    def middleware(self):
        app = AsyncMock()
        return GeoMiddleware(app)

    def test_init(self):
        app = AsyncMock()
        mw = GeoMiddleware(app)
        assert mw.enabled is True

    def test_disabled_middleware(self):
        app = AsyncMock()
        mw = GeoMiddleware(app, enabled=False)
        assert mw.enabled is False


class TestGeoConfig:
    """Tests for config."""

    def test_default_config(self):
        config = GeoConfig()
        assert config.enabled is True
        assert '/health' in config.excluded_paths


class TestGeoStats:
    """Tests for stats."""

    def test_record(self):
        stats = GeoStats()
        stats.record(0.1)
        stats.record(0.2)
        assert stats.total_requests == 2

    def test_get_summary(self):
        stats = GeoStats()
        stats.record(0.1)
        summary = stats.get_summary()
        assert summary['total_requests'] == 1

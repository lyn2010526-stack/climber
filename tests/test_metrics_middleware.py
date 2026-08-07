"""Tests for metrics middleware."""

from unittest.mock import AsyncMock

import pytest

from app.middleware.metrics_middleware import MetricsConfig, MetricsMiddleware, MetricsStats


class TestMetricsMiddleware:
    """Tests for middleware."""

    @pytest.fixture
    def middleware(self):
        app = AsyncMock()
        return MetricsMiddleware(app)

    def test_init(self):
        app = AsyncMock()
        mw = MetricsMiddleware(app)
        assert mw.enabled is True

    def test_disabled_middleware(self):
        app = AsyncMock()
        mw = MetricsMiddleware(app, enabled=False)
        assert mw.enabled is False


class TestMetricsConfig:
    """Tests for config."""

    def test_default_config(self):
        config = MetricsConfig()
        assert config.enabled is True
        assert '/health' in config.excluded_paths


class TestMetricsStats:
    """Tests for stats."""

    def test_record(self):
        stats = MetricsStats()
        stats.record(0.1)
        stats.record(0.2)
        assert stats.total_requests == 2

    def test_get_summary(self):
        stats = MetricsStats()
        stats.record(0.1)
        summary = stats.get_summary()
        assert summary['total_requests'] == 1

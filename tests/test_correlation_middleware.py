"""Tests for correlation middleware."""

from unittest.mock import AsyncMock

import pytest

from app.middleware.correlation_middleware import CorrelationConfig, CorrelationMiddleware, CorrelationStats


class TestCorrelationMiddleware:
    """Tests for middleware."""

    @pytest.fixture
    def middleware(self):
        app = AsyncMock()
        return CorrelationMiddleware(app)

    def test_init(self):
        app = AsyncMock()
        mw = CorrelationMiddleware(app)
        assert mw.enabled is True

    def test_disabled_middleware(self):
        app = AsyncMock()
        mw = CorrelationMiddleware(app, enabled=False)
        assert mw.enabled is False


class TestCorrelationConfig:
    """Tests for config."""

    def test_default_config(self):
        config = CorrelationConfig()
        assert config.enabled is True
        assert '/health' in config.excluded_paths


class TestCorrelationStats:
    """Tests for stats."""

    def test_record(self):
        stats = CorrelationStats()
        stats.record(0.1)
        stats.record(0.2)
        assert stats.total_requests == 2

    def test_get_summary(self):
        stats = CorrelationStats()
        stats.record(0.1)
        summary = stats.get_summary()
        assert summary['total_requests'] == 1

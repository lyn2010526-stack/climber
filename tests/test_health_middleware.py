"""Tests for health middleware."""

from unittest.mock import AsyncMock

import pytest

from app.middleware.health_middleware import HealthConfig, HealthMiddleware, HealthStats


class TestHealthMiddleware:
    """Tests for middleware."""

    @pytest.fixture
    def middleware(self):
        app = AsyncMock()
        return HealthMiddleware(app)

    def test_init(self):
        app = AsyncMock()
        mw = HealthMiddleware(app)
        assert mw.enabled is True

    def test_disabled_middleware(self):
        app = AsyncMock()
        mw = HealthMiddleware(app, enabled=False)
        assert mw.enabled is False


class TestHealthConfig:
    """Tests for config."""

    def test_default_config(self):
        config = HealthConfig()
        assert config.enabled is True
        assert '/health' in config.excluded_paths


class TestHealthStats:
    """Tests for stats."""

    def test_record(self):
        stats = HealthStats()
        stats.record(0.1)
        stats.record(0.2)
        assert stats.total_requests == 2

    def test_get_summary(self):
        stats = HealthStats()
        stats.record(0.1)
        summary = stats.get_summary()
        assert summary['total_requests'] == 1

"""Tests for cors middleware."""

from unittest.mock import AsyncMock

import pytest

from app.middleware.cors_middleware import CorsConfig, CorsMiddleware, CorsStats


class TestCorsMiddleware:
    """Tests for middleware."""

    @pytest.fixture
    def middleware(self):
        app = AsyncMock()
        return CorsMiddleware(app)

    def test_init(self):
        app = AsyncMock()
        mw = CorsMiddleware(app)
        assert mw.enabled is True

    def test_disabled_middleware(self):
        app = AsyncMock()
        mw = CorsMiddleware(app, enabled=False)
        assert mw.enabled is False


class TestCorsConfig:
    """Tests for config."""

    def test_default_config(self):
        config = CorsConfig()
        assert config.enabled is True
        assert '/health' in config.excluded_paths


class TestCorsStats:
    """Tests for stats."""

    def test_record(self):
        stats = CorsStats()
        stats.record(0.1)
        stats.record(0.2)
        assert stats.total_requests == 2

    def test_get_summary(self):
        stats = CorsStats()
        stats.record(0.1)
        summary = stats.get_summary()
        assert summary['total_requests'] == 1

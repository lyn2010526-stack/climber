"""Tests for deprecation middleware."""

from unittest.mock import AsyncMock

import pytest

from app.middleware.deprecation_middleware import DeprecationConfig, DeprecationMiddleware, DeprecationStats


class TestDeprecationMiddleware:
    """Tests for middleware."""

    @pytest.fixture
    def middleware(self):
        app = AsyncMock()
        return DeprecationMiddleware(app)

    def test_init(self):
        app = AsyncMock()
        mw = DeprecationMiddleware(app)
        assert mw.enabled is True

    def test_disabled_middleware(self):
        app = AsyncMock()
        mw = DeprecationMiddleware(app, enabled=False)
        assert mw.enabled is False


class TestDeprecationConfig:
    """Tests for config."""

    def test_default_config(self):
        config = DeprecationConfig()
        assert config.enabled is True
        assert '/health' in config.excluded_paths


class TestDeprecationStats:
    """Tests for stats."""

    def test_record(self):
        stats = DeprecationStats()
        stats.record(0.1)
        stats.record(0.2)
        assert stats.total_requests == 2

    def test_get_summary(self):
        stats = DeprecationStats()
        stats.record(0.1)
        summary = stats.get_summary()
        assert summary['total_requests'] == 1

"""Tests for versioning middleware."""

from unittest.mock import AsyncMock

import pytest

from app.middleware.versioning_middleware import VersioningConfig, VersioningMiddleware, VersioningStats


class TestVersioningMiddleware:
    """Tests for middleware."""

    @pytest.fixture
    def middleware(self):
        app = AsyncMock()
        return VersioningMiddleware(app)

    def test_init(self):
        app = AsyncMock()
        mw = VersioningMiddleware(app)
        assert mw.enabled is True

    def test_disabled_middleware(self):
        app = AsyncMock()
        mw = VersioningMiddleware(app, enabled=False)
        assert mw.enabled is False


class TestVersioningConfig:
    """Tests for config."""

    def test_default_config(self):
        config = VersioningConfig()
        assert config.enabled is True
        assert '/health' in config.excluded_paths


class TestVersioningStats:
    """Tests for stats."""

    def test_record(self):
        stats = VersioningStats()
        stats.record(0.1)
        stats.record(0.2)
        assert stats.total_requests == 2

    def test_get_summary(self):
        stats = VersioningStats()
        stats.record(0.1)
        summary = stats.get_summary()
        assert summary['total_requests'] == 1

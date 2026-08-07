"""Tests for timing middleware."""

from unittest.mock import AsyncMock

import pytest

from app.middleware.timing_middleware import TimingConfig, TimingMiddleware, TimingStats


class TestTimingMiddleware:
    """Tests for middleware."""

    @pytest.fixture
    def middleware(self):
        app = AsyncMock()
        return TimingMiddleware(app)

    def test_init(self):
        app = AsyncMock()
        mw = TimingMiddleware(app)
        assert mw.enabled is True

    def test_disabled_middleware(self):
        app = AsyncMock()
        mw = TimingMiddleware(app, enabled=False)
        assert mw.enabled is False


class TestTimingConfig:
    """Tests for config."""

    def test_default_config(self):
        config = TimingConfig()
        assert config.enabled is True
        assert '/health' in config.excluded_paths


class TestTimingStats:
    """Tests for stats."""

    def test_record(self):
        stats = TimingStats()
        stats.record(0.1)
        stats.record(0.2)
        assert stats.total_requests == 2

    def test_get_summary(self):
        stats = TimingStats()
        stats.record(0.1)
        summary = stats.get_summary()
        assert summary['total_requests'] == 1

"""Tests for logging middleware."""

from unittest.mock import AsyncMock

import pytest

from app.middleware.logging_middleware import LoggingConfig, LoggingMiddleware, LoggingStats


class TestLoggingMiddleware:
    """Tests for middleware."""

    @pytest.fixture
    def middleware(self):
        app = AsyncMock()
        return LoggingMiddleware(app)

    def test_init(self):
        app = AsyncMock()
        mw = LoggingMiddleware(app)
        assert mw.enabled is True

    def test_disabled_middleware(self):
        app = AsyncMock()
        mw = LoggingMiddleware(app, enabled=False)
        assert mw.enabled is False


class TestLoggingConfig:
    """Tests for config."""

    def test_default_config(self):
        config = LoggingConfig()
        assert config.enabled is True
        assert '/health' in config.excluded_paths


class TestLoggingStats:
    """Tests for stats."""

    def test_record(self):
        stats = LoggingStats()
        stats.record(0.1)
        stats.record(0.2)
        assert stats.total_requests == 2

    def test_get_summary(self):
        stats = LoggingStats()
        stats.record(0.1)
        summary = stats.get_summary()
        assert summary['total_requests'] == 1

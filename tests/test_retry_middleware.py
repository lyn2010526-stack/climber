"""Tests for retry middleware."""

from unittest.mock import AsyncMock

import pytest

from app.middleware.retry_middleware import RetryConfig, RetryMiddleware, RetryStats


class TestRetryMiddleware:
    """Tests for middleware."""

    @pytest.fixture
    def middleware(self):
        app = AsyncMock()
        return RetryMiddleware(app)

    def test_init(self):
        app = AsyncMock()
        mw = RetryMiddleware(app)
        assert mw.enabled is True

    def test_disabled_middleware(self):
        app = AsyncMock()
        mw = RetryMiddleware(app, enabled=False)
        assert mw.enabled is False


class TestRetryConfig:
    """Tests for config."""

    def test_default_config(self):
        config = RetryConfig()
        assert config.enabled is True
        assert '/health' in config.excluded_paths


class TestRetryStats:
    """Tests for stats."""

    def test_record(self):
        stats = RetryStats()
        stats.record(0.1)
        stats.record(0.2)
        assert stats.total_requests == 2

    def test_get_summary(self):
        stats = RetryStats()
        stats.record(0.1)
        summary = stats.get_summary()
        assert summary['total_requests'] == 1

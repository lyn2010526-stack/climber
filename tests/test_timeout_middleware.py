"""Tests for timeout middleware."""

from unittest.mock import AsyncMock

import pytest

from app.middleware.timeout_middleware import TimeoutConfig, TimeoutMiddleware, TimeoutStats


class TestTimeoutMiddleware:
    """Tests for middleware."""

    @pytest.fixture
    def middleware(self):
        app = AsyncMock()
        return TimeoutMiddleware(app)

    def test_init(self):
        app = AsyncMock()
        mw = TimeoutMiddleware(app)
        assert mw.enabled is True

    def test_disabled_middleware(self):
        app = AsyncMock()
        mw = TimeoutMiddleware(app, enabled=False)
        assert mw.enabled is False


class TestTimeoutConfig:
    """Tests for config."""

    def test_default_config(self):
        config = TimeoutConfig()
        assert config.enabled is True
        assert '/health' in config.excluded_paths


class TestTimeoutStats:
    """Tests for stats."""

    def test_record(self):
        stats = TimeoutStats()
        stats.record(0.1)
        stats.record(0.2)
        assert stats.total_requests == 2

    def test_get_summary(self):
        stats = TimeoutStats()
        stats.record(0.1)
        summary = stats.get_summary()
        assert summary['total_requests'] == 1

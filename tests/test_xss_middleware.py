"""Tests for xss middleware."""

from unittest.mock import AsyncMock

import pytest

from app.middleware.xss_middleware import XssConfig, XssMiddleware, XssStats


class TestXssMiddleware:
    """Tests for middleware."""

    @pytest.fixture
    def middleware(self):
        app = AsyncMock()
        return XssMiddleware(app)

    def test_init(self):
        app = AsyncMock()
        mw = XssMiddleware(app)
        assert mw.enabled is True

    def test_disabled_middleware(self):
        app = AsyncMock()
        mw = XssMiddleware(app, enabled=False)
        assert mw.enabled is False


class TestXssConfig:
    """Tests for config."""

    def test_default_config(self):
        config = XssConfig()
        assert config.enabled is True
        assert '/health' in config.excluded_paths


class TestXssStats:
    """Tests for stats."""

    def test_record(self):
        stats = XssStats()
        stats.record(0.1)
        stats.record(0.2)
        assert stats.total_requests == 2

    def test_get_summary(self):
        stats = XssStats()
        stats.record(0.1)
        summary = stats.get_summary()
        assert summary['total_requests'] == 1

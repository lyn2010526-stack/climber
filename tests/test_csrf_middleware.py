"""Tests for csrf middleware."""

from unittest.mock import AsyncMock

import pytest

from app.middleware.csrf_middleware import CsrfConfig, CsrfMiddleware, CsrfStats


class TestCsrfMiddleware:
    """Tests for middleware."""

    @pytest.fixture
    def middleware(self):
        app = AsyncMock()
        return CsrfMiddleware(app)

    def test_init(self):
        app = AsyncMock()
        mw = CsrfMiddleware(app)
        assert mw.enabled is True

    def test_disabled_middleware(self):
        app = AsyncMock()
        mw = CsrfMiddleware(app, enabled=False)
        assert mw.enabled is False


class TestCsrfConfig:
    """Tests for config."""

    def test_default_config(self):
        config = CsrfConfig()
        assert config.enabled is True
        assert '/health' in config.excluded_paths


class TestCsrfStats:
    """Tests for stats."""

    def test_record(self):
        stats = CsrfStats()
        stats.record(0.1)
        stats.record(0.2)
        assert stats.total_requests == 2

    def test_get_summary(self):
        stats = CsrfStats()
        stats.record(0.1)
        summary = stats.get_summary()
        assert summary['total_requests'] == 1

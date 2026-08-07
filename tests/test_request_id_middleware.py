"""Tests for request_id middleware."""

from unittest.mock import AsyncMock

import pytest

from app.middleware.request_id_middleware import RequestIdConfig, RequestIdMiddleware, RequestIdStats


class TestRequestIdMiddleware:
    """Tests for middleware."""

    @pytest.fixture
    def middleware(self):
        app = AsyncMock()
        return RequestIdMiddleware(app)

    def test_init(self):
        app = AsyncMock()
        mw = RequestIdMiddleware(app)
        assert mw.enabled is True

    def test_disabled_middleware(self):
        app = AsyncMock()
        mw = RequestIdMiddleware(app, enabled=False)
        assert mw.enabled is False


class TestRequestIdConfig:
    """Tests for config."""

    def test_default_config(self):
        config = RequestIdConfig()
        assert config.enabled is True
        assert '/health' in config.excluded_paths


class TestRequestIdStats:
    """Tests for stats."""

    def test_record(self):
        stats = RequestIdStats()
        stats.record(0.1)
        stats.record(0.2)
        assert stats.total_requests == 2

    def test_get_summary(self):
        stats = RequestIdStats()
        stats.record(0.1)
        summary = stats.get_summary()
        assert summary['total_requests'] == 1

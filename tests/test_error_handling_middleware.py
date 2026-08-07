"""Tests for error_handling middleware."""

from unittest.mock import AsyncMock

import pytest

from app.middleware.error_handling_middleware import ErrorHandlingConfig, ErrorHandlingMiddleware, ErrorHandlingStats


class TestErrorHandlingMiddleware:
    """Tests for middleware."""

    @pytest.fixture
    def middleware(self):
        app = AsyncMock()
        return ErrorHandlingMiddleware(app)

    def test_init(self):
        app = AsyncMock()
        mw = ErrorHandlingMiddleware(app)
        assert mw.enabled is True

    def test_disabled_middleware(self):
        app = AsyncMock()
        mw = ErrorHandlingMiddleware(app, enabled=False)
        assert mw.enabled is False


class TestErrorHandlingConfig:
    """Tests for config."""

    def test_default_config(self):
        config = ErrorHandlingConfig()
        assert config.enabled is True
        assert '/health' in config.excluded_paths


class TestErrorHandlingStats:
    """Tests for stats."""

    def test_record(self):
        stats = ErrorHandlingStats()
        stats.record(0.1)
        stats.record(0.2)
        assert stats.total_requests == 2

    def test_get_summary(self):
        stats = ErrorHandlingStats()
        stats.record(0.1)
        summary = stats.get_summary()
        assert summary['total_requests'] == 1

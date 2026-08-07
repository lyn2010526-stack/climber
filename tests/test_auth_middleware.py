"""Tests for auth middleware."""

from unittest.mock import AsyncMock

import pytest

from app.middleware.auth_middleware import AuthConfig, AuthMiddleware, AuthStats


class TestAuthMiddleware:
    """Tests for middleware."""

    @pytest.fixture
    def middleware(self):
        app = AsyncMock()
        return AuthMiddleware(app)

    def test_init(self):
        app = AsyncMock()
        mw = AuthMiddleware(app)
        assert mw.enabled is True

    def test_disabled_middleware(self):
        app = AsyncMock()
        mw = AuthMiddleware(app, enabled=False)
        assert mw.enabled is False


class TestAuthConfig:
    """Tests for config."""

    def test_default_config(self):
        config = AuthConfig()
        assert config.enabled is True
        assert '/health' in config.excluded_paths


class TestAuthStats:
    """Tests for stats."""

    def test_record(self):
        stats = AuthStats()
        stats.record(0.1)
        stats.record(0.2)
        assert stats.total_requests == 2

    def test_get_summary(self):
        stats = AuthStats()
        stats.record(0.1)
        summary = stats.get_summary()
        assert summary['total_requests'] == 1

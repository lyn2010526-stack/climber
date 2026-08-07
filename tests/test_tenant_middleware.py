"""Tests for tenant middleware."""

from unittest.mock import AsyncMock

import pytest

from app.middleware.tenant_middleware import TenantConfig, TenantMiddleware, TenantStats


class TestTenantMiddleware:
    """Tests for middleware."""

    @pytest.fixture
    def middleware(self):
        app = AsyncMock()
        return TenantMiddleware(app)

    def test_init(self):
        app = AsyncMock()
        mw = TenantMiddleware(app)
        assert mw.enabled is True

    def test_disabled_middleware(self):
        app = AsyncMock()
        mw = TenantMiddleware(app, enabled=False)
        assert mw.enabled is False


class TestTenantConfig:
    """Tests for config."""

    def test_default_config(self):
        config = TenantConfig()
        assert config.enabled is True
        assert '/health' in config.excluded_paths


class TestTenantStats:
    """Tests for stats."""

    def test_record(self):
        stats = TenantStats()
        stats.record(0.1)
        stats.record(0.2)
        assert stats.total_requests == 2

    def test_get_summary(self):
        stats = TenantStats()
        stats.record(0.1)
        summary = stats.get_summary()
        assert summary['total_requests'] == 1

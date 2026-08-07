"""Tests for maintenance middleware."""

from unittest.mock import AsyncMock

import pytest

from app.middleware.maintenance_middleware import MaintenanceConfig, MaintenanceMiddleware, MaintenanceStats


class TestMaintenanceMiddleware:
    """Tests for middleware."""

    @pytest.fixture
    def middleware(self):
        app = AsyncMock()
        return MaintenanceMiddleware(app)

    def test_init(self):
        app = AsyncMock()
        mw = MaintenanceMiddleware(app)
        assert mw.enabled is True

    def test_disabled_middleware(self):
        app = AsyncMock()
        mw = MaintenanceMiddleware(app, enabled=False)
        assert mw.enabled is False


class TestMaintenanceConfig:
    """Tests for config."""

    def test_default_config(self):
        config = MaintenanceConfig()
        assert config.enabled is True
        assert '/health' in config.excluded_paths


class TestMaintenanceStats:
    """Tests for stats."""

    def test_record(self):
        stats = MaintenanceStats()
        stats.record(0.1)
        stats.record(0.2)
        assert stats.total_requests == 2

    def test_get_summary(self):
        stats = MaintenanceStats()
        stats.record(0.1)
        summary = stats.get_summary()
        assert summary['total_requests'] == 1

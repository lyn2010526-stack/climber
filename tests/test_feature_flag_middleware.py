"""Tests for feature_flag middleware."""

from unittest.mock import AsyncMock

import pytest

from app.middleware.feature_flag_middleware import FeatureFlagConfig, FeatureFlagMiddleware, FeatureFlagStats


class TestFeatureFlagMiddleware:
    """Tests for middleware."""

    @pytest.fixture
    def middleware(self):
        app = AsyncMock()
        return FeatureFlagMiddleware(app)

    def test_init(self):
        app = AsyncMock()
        mw = FeatureFlagMiddleware(app)
        assert mw.enabled is True

    def test_disabled_middleware(self):
        app = AsyncMock()
        mw = FeatureFlagMiddleware(app, enabled=False)
        assert mw.enabled is False


class TestFeatureFlagConfig:
    """Tests for config."""

    def test_default_config(self):
        config = FeatureFlagConfig()
        assert config.enabled is True
        assert '/health' in config.excluded_paths


class TestFeatureFlagStats:
    """Tests for stats."""

    def test_record(self):
        stats = FeatureFlagStats()
        stats.record(0.1)
        stats.record(0.2)
        assert stats.total_requests == 2

    def test_get_summary(self):
        stats = FeatureFlagStats()
        stats.record(0.1)
        summary = stats.get_summary()
        assert summary['total_requests'] == 1

"""Tests for validation middleware."""

from unittest.mock import AsyncMock

import pytest

from app.middleware.validation_middleware import ValidationConfig, ValidationMiddleware, ValidationStats


class TestValidationMiddleware:
    """Tests for middleware."""

    @pytest.fixture
    def middleware(self):
        app = AsyncMock()
        return ValidationMiddleware(app)

    def test_init(self):
        app = AsyncMock()
        mw = ValidationMiddleware(app)
        assert mw.enabled is True

    def test_disabled_middleware(self):
        app = AsyncMock()
        mw = ValidationMiddleware(app, enabled=False)
        assert mw.enabled is False


class TestValidationConfig:
    """Tests for config."""

    def test_default_config(self):
        config = ValidationConfig()
        assert config.enabled is True
        assert '/health' in config.excluded_paths


class TestValidationStats:
    """Tests for stats."""

    def test_record(self):
        stats = ValidationStats()
        stats.record(0.1)
        stats.record(0.2)
        assert stats.total_requests == 2

    def test_get_summary(self):
        stats = ValidationStats()
        stats.record(0.1)
        summary = stats.get_summary()
        assert summary['total_requests'] == 1

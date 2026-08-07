"""Tests for compression middleware."""

from unittest.mock import AsyncMock

import pytest

from app.middleware.compression_middleware import CompressionConfig, CompressionMiddleware, CompressionStats


class TestCompressionMiddleware:
    """Tests for middleware."""

    @pytest.fixture
    def middleware(self):
        app = AsyncMock()
        return CompressionMiddleware(app)

    def test_init(self):
        app = AsyncMock()
        mw = CompressionMiddleware(app)
        assert mw.enabled is True

    def test_disabled_middleware(self):
        app = AsyncMock()
        mw = CompressionMiddleware(app, enabled=False)
        assert mw.enabled is False


class TestCompressionConfig:
    """Tests for config."""

    def test_default_config(self):
        config = CompressionConfig()
        assert config.enabled is True
        assert '/health' in config.excluded_paths


class TestCompressionStats:
    """Tests for stats."""

    def test_record(self):
        stats = CompressionStats()
        stats.record(0.1)
        stats.record(0.2)
        assert stats.total_requests == 2

    def test_get_summary(self):
        stats = CompressionStats()
        stats.record(0.1)
        summary = stats.get_summary()
        assert summary['total_requests'] == 1

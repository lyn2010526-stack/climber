"""Tests for bot_detection middleware."""

from unittest.mock import AsyncMock

import pytest

from app.middleware.bot_detection_middleware import BotDetectionConfig, BotDetectionMiddleware, BotDetectionStats


class TestBotDetectionMiddleware:
    """Tests for middleware."""

    @pytest.fixture
    def middleware(self):
        app = AsyncMock()
        return BotDetectionMiddleware(app)

    def test_init(self):
        app = AsyncMock()
        mw = BotDetectionMiddleware(app)
        assert mw.enabled is True

    def test_disabled_middleware(self):
        app = AsyncMock()
        mw = BotDetectionMiddleware(app, enabled=False)
        assert mw.enabled is False


class TestBotDetectionConfig:
    """Tests for config."""

    def test_default_config(self):
        config = BotDetectionConfig()
        assert config.enabled is True
        assert '/health' in config.excluded_paths


class TestBotDetectionStats:
    """Tests for stats."""

    def test_record(self):
        stats = BotDetectionStats()
        stats.record(0.1)
        stats.record(0.2)
        assert stats.total_requests == 2

    def test_get_summary(self):
        stats = BotDetectionStats()
        stats.record(0.1)
        summary = stats.get_summary()
        assert summary['total_requests'] == 1

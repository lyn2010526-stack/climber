"""Tests for analytics config."""

import os

from app.configs.analytics_config import AnalyticsAppConfig


class TestAnalyticsAppConfig:
    """Tests for app config."""

    def test_default_config(self):
        config = AnalyticsAppConfig()
        assert config.environment == 'development'
        assert config.debug is False

    def test_from_env(self):
        os.environ['APP_ENV'] = 'testing'
        config = AnalyticsAppConfig.from_env()
        assert config.environment == 'testing'

    def test_validate_production(self):
        config = AnalyticsAppConfig(environment='production')
        errors = config.validate()
        assert len(errors) > 0

    def test_validate_development(self):
        config = AnalyticsAppConfig(environment='development')
        errors = config.validate()
        assert len(errors) == 0

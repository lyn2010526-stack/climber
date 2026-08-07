"""Tests for logging config."""

import os

from app.configs.logging_config import LoggingAppConfig


class TestLoggingAppConfig:
    """Tests for app config."""

    def test_default_config(self):
        config = LoggingAppConfig()
        assert config.environment == 'development'
        assert config.debug is False

    def test_from_env(self):
        os.environ['APP_ENV'] = 'testing'
        config = LoggingAppConfig.from_env()
        assert config.environment == 'testing'

    def test_validate_production(self):
        config = LoggingAppConfig(environment='production')
        errors = config.validate()
        assert len(errors) > 0

    def test_validate_development(self):
        config = LoggingAppConfig(environment='development')
        errors = config.validate()
        assert len(errors) == 0

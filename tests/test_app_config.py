"""Tests for app config."""

import os

from app.configs.app_config import AppAppConfig


class TestAppAppConfig:
    """Tests for app config."""

    def test_default_config(self):
        config = AppAppConfig()
        assert config.environment == 'development'
        assert config.debug is False

    def test_from_env(self):
        os.environ['APP_ENV'] = 'testing'
        config = AppAppConfig.from_env()
        assert config.environment == 'testing'

    def test_validate_production(self):
        config = AppAppConfig(environment='production')
        errors = config.validate()
        assert len(errors) > 0

    def test_validate_development(self):
        config = AppAppConfig(environment='development')
        errors = config.validate()
        assert len(errors) == 0

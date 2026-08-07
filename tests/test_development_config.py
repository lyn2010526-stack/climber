"""Tests for development config."""

import os

from app.configs.development_config import DevelopmentAppConfig


class TestDevelopmentAppConfig:
    """Tests for app config."""

    def test_default_config(self):
        config = DevelopmentAppConfig()
        assert config.environment == 'development'
        assert config.debug is False

    def test_from_env(self):
        os.environ['APP_ENV'] = 'testing'
        config = DevelopmentAppConfig.from_env()
        assert config.environment == 'testing'

    def test_validate_production(self):
        config = DevelopmentAppConfig(environment='production')
        errors = config.validate()
        assert len(errors) > 0

    def test_validate_development(self):
        config = DevelopmentAppConfig(environment='development')
        errors = config.validate()
        assert len(errors) == 0

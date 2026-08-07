"""Tests for cors config."""

import os

from app.configs.cors_config import CorsAppConfig


class TestCorsAppConfig:
    """Tests for app config."""

    def test_default_config(self):
        config = CorsAppConfig()
        assert config.environment == 'development'
        assert config.debug is False

    def test_from_env(self):
        os.environ['APP_ENV'] = 'testing'
        config = CorsAppConfig.from_env()
        assert config.environment == 'testing'

    def test_validate_production(self):
        config = CorsAppConfig(environment='production')
        errors = config.validate()
        assert len(errors) > 0

    def test_validate_development(self):
        config = CorsAppConfig(environment='development')
        errors = config.validate()
        assert len(errors) == 0

"""Tests for security config."""

import os

from app.configs.security_config import SecurityAppConfig


class TestSecurityAppConfig:
    """Tests for app config."""

    def test_default_config(self):
        config = SecurityAppConfig()
        assert config.environment == 'development'
        assert config.debug is False

    def test_from_env(self):
        os.environ['APP_ENV'] = 'testing'
        config = SecurityAppConfig.from_env()
        assert config.environment == 'testing'

    def test_validate_production(self):
        config = SecurityAppConfig(environment='production')
        errors = config.validate()
        assert len(errors) > 0

    def test_validate_development(self):
        config = SecurityAppConfig(environment='development')
        errors = config.validate()
        assert len(errors) == 0

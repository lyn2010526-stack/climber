"""Tests for auth config."""

import os

from app.configs.auth_config import AuthAppConfig


class TestAuthAppConfig:
    """Tests for app config."""

    def test_default_config(self):
        config = AuthAppConfig()
        assert config.environment == 'development'
        assert config.debug is False

    def test_from_env(self):
        os.environ['APP_ENV'] = 'testing'
        config = AuthAppConfig.from_env()
        assert config.environment == 'testing'

    def test_validate_production(self):
        config = AuthAppConfig(environment='production')
        errors = config.validate()
        assert len(errors) > 0

    def test_validate_development(self):
        config = AuthAppConfig(environment='development')
        errors = config.validate()
        assert len(errors) == 0

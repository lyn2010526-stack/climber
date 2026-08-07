"""Tests for server config."""

import os

from app.configs.server_config import ServerAppConfig


class TestServerAppConfig:
    """Tests for app config."""

    def test_default_config(self):
        config = ServerAppConfig()
        assert config.environment == 'development'
        assert config.debug is False

    def test_from_env(self):
        os.environ['APP_ENV'] = 'testing'
        config = ServerAppConfig.from_env()
        assert config.environment == 'testing'

    def test_validate_production(self):
        config = ServerAppConfig(environment='production')
        errors = config.validate()
        assert len(errors) > 0

    def test_validate_development(self):
        config = ServerAppConfig(environment='development')
        errors = config.validate()
        assert len(errors) == 0

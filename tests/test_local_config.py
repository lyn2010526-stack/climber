"""Tests for local config."""

import os

from app.configs.local_config import LocalAppConfig


class TestLocalAppConfig:
    """Tests for app config."""

    def test_default_config(self):
        config = LocalAppConfig()
        assert config.environment == 'development'
        assert config.debug is False

    def test_from_env(self):
        os.environ['APP_ENV'] = 'testing'
        config = LocalAppConfig.from_env()
        assert config.environment == 'testing'

    def test_validate_production(self):
        config = LocalAppConfig(environment='production')
        errors = config.validate()
        assert len(errors) > 0

    def test_validate_development(self):
        config = LocalAppConfig(environment='development')
        errors = config.validate()
        assert len(errors) == 0

"""Tests for integrations config."""

import os

from app.configs.integrations_config import IntegrationsAppConfig


class TestIntegrationsAppConfig:
    """Tests for app config."""

    def test_default_config(self):
        config = IntegrationsAppConfig()
        assert config.environment == 'development'
        assert config.debug is False

    def test_from_env(self):
        os.environ['APP_ENV'] = 'testing'
        config = IntegrationsAppConfig.from_env()
        assert config.environment == 'testing'

    def test_validate_production(self):
        config = IntegrationsAppConfig(environment='production')
        errors = config.validate()
        assert len(errors) > 0

    def test_validate_development(self):
        config = IntegrationsAppConfig(environment='development')
        errors = config.validate()
        assert len(errors) == 0

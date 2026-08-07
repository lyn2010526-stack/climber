"""Tests for alerting config."""

import os

from app.configs.alerting_config import AlertingAppConfig


class TestAlertingAppConfig:
    """Tests for app config."""

    def test_default_config(self):
        config = AlertingAppConfig()
        assert config.environment == 'development'
        assert config.debug is False

    def test_from_env(self):
        os.environ['APP_ENV'] = 'testing'
        config = AlertingAppConfig.from_env()
        assert config.environment == 'testing'

    def test_validate_production(self):
        config = AlertingAppConfig(environment='production')
        errors = config.validate()
        assert len(errors) > 0

    def test_validate_development(self):
        config = AlertingAppConfig(environment='development')
        errors = config.validate()
        assert len(errors) == 0

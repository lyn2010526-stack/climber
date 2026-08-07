"""Tests for monitoring config."""

import os

from app.configs.monitoring_config import MonitoringAppConfig


class TestMonitoringAppConfig:
    """Tests for app config."""

    def test_default_config(self):
        config = MonitoringAppConfig()
        assert config.environment == 'development'
        assert config.debug is False

    def test_from_env(self):
        os.environ['APP_ENV'] = 'testing'
        config = MonitoringAppConfig.from_env()
        assert config.environment == 'testing'

    def test_validate_production(self):
        config = MonitoringAppConfig(environment='production')
        errors = config.validate()
        assert len(errors) > 0

    def test_validate_development(self):
        config = MonitoringAppConfig(environment='development')
        errors = config.validate()
        assert len(errors) == 0

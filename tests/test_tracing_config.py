"""Tests for tracing config."""

import os

from app.configs.tracing_config import TracingAppConfig


class TestTracingAppConfig:
    """Tests for app config."""

    def test_default_config(self):
        config = TracingAppConfig()
        assert config.environment == 'development'
        assert config.debug is False

    def test_from_env(self):
        os.environ['APP_ENV'] = 'testing'
        config = TracingAppConfig.from_env()
        assert config.environment == 'testing'

    def test_validate_production(self):
        config = TracingAppConfig(environment='production')
        errors = config.validate()
        assert len(errors) > 0

    def test_validate_development(self):
        config = TracingAppConfig(environment='development')
        errors = config.validate()
        assert len(errors) == 0

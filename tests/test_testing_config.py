"""Tests for testing config."""

import os

from app.configs.testing_config import TestingAppConfig


class TestTestingAppConfig:
    """Tests for app config."""

    def test_default_config(self):
        config = TestingAppConfig()
        assert config.environment == 'development'
        assert config.debug is False

    def test_from_env(self):
        os.environ['APP_ENV'] = 'testing'
        config = TestingAppConfig.from_env()
        assert config.environment == 'testing'

    def test_validate_production(self):
        config = TestingAppConfig(environment='production')
        errors = config.validate()
        assert len(errors) > 0

    def test_validate_development(self):
        config = TestingAppConfig(environment='development')
        errors = config.validate()
        assert len(errors) == 0

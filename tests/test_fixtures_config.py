"""Tests for fixtures config."""

import os

from app.configs.fixtures_config import FixturesAppConfig


class TestFixturesAppConfig:
    """Tests for app config."""

    def test_default_config(self):
        config = FixturesAppConfig()
        assert config.environment == 'development'
        assert config.debug is False

    def test_from_env(self):
        os.environ['APP_ENV'] = 'testing'
        config = FixturesAppConfig.from_env()
        assert config.environment == 'testing'

    def test_validate_production(self):
        config = FixturesAppConfig(environment='production')
        errors = config.validate()
        assert len(errors) > 0

    def test_validate_development(self):
        config = FixturesAppConfig(environment='development')
        errors = config.validate()
        assert len(errors) == 0

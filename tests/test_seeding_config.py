"""Tests for seeding config."""

import os

from app.configs.seeding_config import SeedingAppConfig


class TestSeedingAppConfig:
    """Tests for app config."""

    def test_default_config(self):
        config = SeedingAppConfig()
        assert config.environment == 'development'
        assert config.debug is False

    def test_from_env(self):
        os.environ['APP_ENV'] = 'testing'
        config = SeedingAppConfig.from_env()
        assert config.environment == 'testing'

    def test_validate_production(self):
        config = SeedingAppConfig(environment='production')
        errors = config.validate()
        assert len(errors) > 0

    def test_validate_development(self):
        config = SeedingAppConfig(environment='development')
        errors = config.validate()
        assert len(errors) == 0

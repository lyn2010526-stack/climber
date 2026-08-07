"""Tests for migration config."""

import os

from app.configs.migration_config import MigrationAppConfig


class TestMigrationAppConfig:
    """Tests for app config."""

    def test_default_config(self):
        config = MigrationAppConfig()
        assert config.environment == 'development'
        assert config.debug is False

    def test_from_env(self):
        os.environ['APP_ENV'] = 'testing'
        config = MigrationAppConfig.from_env()
        assert config.environment == 'testing'

    def test_validate_production(self):
        config = MigrationAppConfig(environment='production')
        errors = config.validate()
        assert len(errors) > 0

    def test_validate_development(self):
        config = MigrationAppConfig(environment='development')
        errors = config.validate()
        assert len(errors) == 0

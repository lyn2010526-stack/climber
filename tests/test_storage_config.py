"""Tests for storage config."""

import os

from app.configs.storage_config import StorageAppConfig


class TestStorageAppConfig:
    """Tests for app config."""

    def test_default_config(self):
        config = StorageAppConfig()
        assert config.environment == 'development'
        assert config.debug is False

    def test_from_env(self):
        os.environ['APP_ENV'] = 'testing'
        config = StorageAppConfig.from_env()
        assert config.environment == 'testing'

    def test_validate_production(self):
        config = StorageAppConfig(environment='production')
        errors = config.validate()
        assert len(errors) > 0

    def test_validate_development(self):
        config = StorageAppConfig(environment='development')
        errors = config.validate()
        assert len(errors) == 0

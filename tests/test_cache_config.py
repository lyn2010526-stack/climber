"""Tests for cache config."""

import os

from app.configs.cache_config import CacheAppConfig


class TestCacheAppConfig:
    """Tests for app config."""

    def test_default_config(self):
        config = CacheAppConfig()
        assert config.environment == 'development'
        assert config.debug is False

    def test_from_env(self):
        os.environ['APP_ENV'] = 'testing'
        config = CacheAppConfig.from_env()
        assert config.environment == 'testing'

    def test_validate_production(self):
        config = CacheAppConfig(environment='production')
        errors = config.validate()
        assert len(errors) > 0

    def test_validate_development(self):
        config = CacheAppConfig(environment='development')
        errors = config.validate()
        assert len(errors) == 0

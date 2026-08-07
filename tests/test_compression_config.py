"""Tests for compression config."""

import os

from app.configs.compression_config import CompressionAppConfig


class TestCompressionAppConfig:
    """Tests for app config."""

    def test_default_config(self):
        config = CompressionAppConfig()
        assert config.environment == 'development'
        assert config.debug is False

    def test_from_env(self):
        os.environ['APP_ENV'] = 'testing'
        config = CompressionAppConfig.from_env()
        assert config.environment == 'testing'

    def test_validate_production(self):
        config = CompressionAppConfig(environment='production')
        errors = config.validate()
        assert len(errors) > 0

    def test_validate_development(self):
        config = CompressionAppConfig(environment='development')
        errors = config.validate()
        assert len(errors) == 0

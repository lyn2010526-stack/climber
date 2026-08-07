"""Tests for features config."""

import os

from app.configs.features_config import FeaturesAppConfig


class TestFeaturesAppConfig:
    """Tests for app config."""

    def test_default_config(self):
        config = FeaturesAppConfig()
        assert config.environment == 'development'
        assert config.debug is False

    def test_from_env(self):
        os.environ['APP_ENV'] = 'testing'
        config = FeaturesAppConfig.from_env()
        assert config.environment == 'testing'

    def test_validate_production(self):
        config = FeaturesAppConfig(environment='production')
        errors = config.validate()
        assert len(errors) > 0

    def test_validate_development(self):
        config = FeaturesAppConfig(environment='development')
        errors = config.validate()
        assert len(errors) == 0

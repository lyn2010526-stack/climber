"""Tests for production config."""

import os

from app.configs.production_config import ProductionAppConfig


class TestProductionAppConfig:
    """Tests for app config."""

    def test_default_config(self):
        config = ProductionAppConfig()
        assert config.environment == 'development'
        assert config.debug is False

    def test_from_env(self):
        os.environ['APP_ENV'] = 'testing'
        config = ProductionAppConfig.from_env()
        assert config.environment == 'testing'

    def test_validate_production(self):
        config = ProductionAppConfig(environment='production')
        errors = config.validate()
        assert len(errors) > 0

    def test_validate_development(self):
        config = ProductionAppConfig(environment='development')
        errors = config.validate()
        assert len(errors) == 0

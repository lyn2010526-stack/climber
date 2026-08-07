"""Tests for search config."""

import os

from app.configs.search_config import SearchAppConfig


class TestSearchAppConfig:
    """Tests for app config."""

    def test_default_config(self):
        config = SearchAppConfig()
        assert config.environment == 'development'
        assert config.debug is False

    def test_from_env(self):
        os.environ['APP_ENV'] = 'testing'
        config = SearchAppConfig.from_env()
        assert config.environment == 'testing'

    def test_validate_production(self):
        config = SearchAppConfig(environment='production')
        errors = config.validate()
        assert len(errors) > 0

    def test_validate_development(self):
        config = SearchAppConfig(environment='development')
        errors = config.validate()
        assert len(errors) == 0

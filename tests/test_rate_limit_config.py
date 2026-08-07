"""Tests for rate_limit config."""

import os

from app.configs.rate_limit_config import RateLimitAppConfig


class TestRateLimitAppConfig:
    """Tests for app config."""

    def test_default_config(self):
        config = RateLimitAppConfig()
        assert config.environment == 'development'
        assert config.debug is False

    def test_from_env(self):
        os.environ['APP_ENV'] = 'testing'
        config = RateLimitAppConfig.from_env()
        assert config.environment == 'testing'

    def test_validate_production(self):
        config = RateLimitAppConfig(environment='production')
        errors = config.validate()
        assert len(errors) > 0

    def test_validate_development(self):
        config = RateLimitAppConfig(environment='development')
        errors = config.validate()
        assert len(errors) == 0

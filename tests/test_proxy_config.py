"""Tests for proxy config."""

import os

from app.configs.proxy_config import ProxyAppConfig


class TestProxyAppConfig:
    """Tests for app config."""

    def test_default_config(self):
        config = ProxyAppConfig()
        assert config.environment == 'development'
        assert config.debug is False

    def test_from_env(self):
        os.environ['APP_ENV'] = 'testing'
        config = ProxyAppConfig.from_env()
        assert config.environment == 'testing'

    def test_validate_production(self):
        config = ProxyAppConfig(environment='production')
        errors = config.validate()
        assert len(errors) > 0

    def test_validate_development(self):
        config = ProxyAppConfig(environment='development')
        errors = config.validate()
        assert len(errors) == 0

"""Tests for email config."""

import os

from app.configs.email_config import EmailAppConfig


class TestEmailAppConfig:
    """Tests for app config."""

    def test_default_config(self):
        config = EmailAppConfig()
        assert config.environment == 'development'
        assert config.debug is False

    def test_from_env(self):
        os.environ['APP_ENV'] = 'testing'
        config = EmailAppConfig.from_env()
        assert config.environment == 'testing'

    def test_validate_production(self):
        config = EmailAppConfig(environment='production')
        errors = config.validate()
        assert len(errors) > 0

    def test_validate_development(self):
        config = EmailAppConfig(environment='development')
        errors = config.validate()
        assert len(errors) == 0

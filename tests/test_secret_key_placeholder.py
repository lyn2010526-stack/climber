"""A placeholder secret must not boot a deployed instance.

`_require_stable_secret` in app/config.py returned as soon as `app_secret_key`
was truthy. The standard first step for a new deployment is to copy
`.env.example` to `.env`, so a truthy placeholder satisfied every check while a
publicly known string stayed in charge of signing tokens and of the Fernet key
that encrypts stored third-party provider credentials.

These tests pin the behaviour: a placeholder is rejected in production and
staging, local development still boots, and the existing auth guards keep
working.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import MIN_SECRET_LENGTH, Settings, is_placeholder_secret

STRONG = "k3M9xQ2vLp7Rt4wYzA8bN1cD6fH0jS5uE2gV7nI4oP1l"


def build(**overrides) -> Settings:
    base = {"app_env": "production", "app_secret_key": STRONG}
    return Settings(**{**base, **overrides})


class TestIsPlaceholderSecret:
    def test_strong_secret_is_accepted(self):
        assert is_placeholder_secret(STRONG) is False

    @pytest.mark.parametrize(
        "value",
        [
            "change-me-in-production",
            "changeme",
            "your-secret-key",
            "replace-me",
            "placeholder",
            "example",
            "secret",
            "todo",
            "xxx",
        ],
    )
    def test_documented_placeholders_are_rejected(self, value):
        assert is_placeholder_secret(value) is True

    def test_matching_is_case_insensitive(self):
        assert is_placeholder_secret("CHANGE-ME-IN-PRODUCTION") is True

    def test_surrounding_whitespace_is_ignored(self):
        assert is_placeholder_secret("  changeme  ") is True

    def test_short_secret_is_rejected(self):
        assert is_placeholder_secret("a" * (MIN_SECRET_LENGTH - 1)) is True

    def test_minimum_length_secret_is_accepted(self):
        assert is_placeholder_secret("a" * MIN_SECRET_LENGTH) is False

    def test_secret_merely_containing_a_marker_is_accepted(self):
        # Exact matching keeps a real key such as this one from being refused
        # just because it embeds a word like "example".
        value = "not-an-example-secret-long-enough-32"
        assert is_placeholder_secret(value) is False

    def test_empty_value_is_treated_as_placeholder(self):
        assert is_placeholder_secret("") is True


class TestDeployedBootsRejectPlaceholders:
    @pytest.mark.parametrize("environment", ["production", "prod", "staging"])
    @pytest.mark.parametrize("value", ["change-me-in-production", "changeme", "short"])
    def test_boot_fails(self, environment, value):
        with pytest.raises(ValidationError, match="placeholder"):
            build(app_env=environment, app_secret_key=value)

    @pytest.mark.parametrize("environment", ["production", "prod", "staging"])
    def test_strong_secret_boots(self, environment):
        assert build(app_env=environment).app_secret_key == STRONG


class TestLocalBootsKeepWorking:
    @pytest.mark.parametrize("environment", ["local", "development", "test", "testing"])
    def test_placeholder_is_tolerated(self, environment):
        assert build(app_env=environment, app_secret_key="changeme").app_secret_key

    @pytest.mark.parametrize("environment", ["local", "development", "test", "testing"])
    def test_empty_secret_gets_dev_fallback(self, environment):
        settings = build(app_env=environment, app_secret_key="")
        assert settings.app_secret_key == "agent-engine-local-persistent-development-key"


class TestExistingGuardsStillHold:
    def test_production_without_auth_still_fails(self):
        with pytest.raises(ValidationError, match="ENABLE_AUTH"):
            build(enable_auth=False)

    def test_production_without_secret_still_fails(self):
        with pytest.raises(ValidationError, match="APP_SECRET_KEY"):
            build(app_secret_key="")

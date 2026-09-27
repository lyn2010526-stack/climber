"""Secret key validation tests.

`_require_stable_secret` (app/config.py) returned immediately whenever
`app_secret_key` was truthy. `.env.example` ships
`APP_SECRET_KEY=change-me-in-production`, and the standard first step for any
new deployment is to copy that file to `.env` - so a truthy placeholder
skipped every check, including the production requirement, and left a publicly
known string as the signing key.

That key is also the input to `api_key_crypto`, which derives the Fernet key
used to encrypt stored third-party provider API keys, so a known signing key
means those credentials are decryptable too.

These tests pin the fixed behaviour: a placeholder is rejected regardless of
environment, production requires a real key, and local development still gets
a working value.
"""

from __future__ import annotations

import pytest

PLACEHOLDERS = (
    "change-me-in-production",
    "changeme",
    "your-secret-key",
    "your_secret_key_here",
    "secret",
    "changethis",
    "replace-me",
    "xxx",
    "todo",
)


def _settings(**overrides):
    """Build a Settings instance with an explicit environment.

    `app_testing` is forced off because tests/conftest.py sets APP_TESTING=true
    process-wide, and the validator deliberately supplies a development key in
    that mode. Leaving it on would make every production assertion pass for
    the wrong reason.
    """
    from app.config import Settings

    base = {"app_env": "production", "app_secret_key": "", "app_testing": False}
    base.update(overrides)
    return Settings(**base)


@pytest.mark.parametrize("placeholder", PLACEHOLDERS)
def test_placeholders_are_rejected_in_production(placeholder) -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        _settings(app_secret_key=placeholder)


def test_a_real_production_key_is_accepted() -> None:
    settings = _settings(app_secret_key="k" * 48)
    assert settings.app_secret_key == "k" * 48


def test_production_without_a_key_fails() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        _settings(app_secret_key="")


def test_local_development_still_gets_a_working_key() -> None:
    """Tests and local runs must not be forced to configure a secret."""
    settings = _settings(app_env="local", app_secret_key="")
    assert settings.app_secret_key


def test_a_configured_local_key_is_left_alone() -> None:
    settings = _settings(app_env="local", app_secret_key="local-dev-key-123456")
    assert settings.app_secret_key == "local-dev-key-123456"


def test_placeholder_detection_ignores_surrounding_whitespace() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        _settings(app_secret_key="  change-me-in-production  ")


def test_placeholder_detection_is_case_insensitive() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        _settings(app_secret_key="CHANGE-ME-IN-PRODUCTION")


def test_env_example_does_not_ship_a_usable_placeholder() -> None:
    """The file new deployments copy must not contain a passing value."""
    from pathlib import Path

    example = Path(".env.example")
    assert example.is_file(), ".env.example fixture is missing from the checkout"

    text = example.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("APP_SECRET_KEY="):
            value = line.split("=", 1)[1].strip()
            assert value == "", (
                "APP_SECRET_KEY in .env.example must be empty; a placeholder "
                "value passes the truthy check and becomes the signing key"
            )
            return
    pytest.fail("APP_SECRET_KEY not found in .env.example")


def test_api_key_crypto_does_not_fall_back_to_a_repo_literal() -> None:
    """The Fernet key must derive from settings, not a duplicated literal."""
    from pathlib import Path

    source = Path("app/core/api_key_crypto.py").read_text(encoding="utf-8")
    assert "agent-engine-local-persistent-development-key" not in source

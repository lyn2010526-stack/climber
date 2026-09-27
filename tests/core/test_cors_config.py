"""CORS configuration tests.

`Settings` declared both `cors_origins` (a comma-separated string, the field
documented in README:186 and .env.example:29) and `cors_origins_list` (a list
with its own default). main.py:251 read the list, so the documented variable
was read by nothing: setting CORS_ORIGINS to a new origin silently did nothing
on the running server.

The second half of the risk is the combination that matters: main.py hardcodes
`allow_credentials=True`, and Starlette reflects the request Origin when
`allow_all_origins` and `allow_credentials` are both set. A wildcard allowlist
therefore means any site can call the API with credentials attached.

These tests pin one source of truth and refuse the wildcard combination.
"""

from __future__ import annotations

import pytest


def _settings(**overrides):
    from app.config import Settings

    base = {"app_env": "local", "app_secret_key": "", "app_testing": True}
    base.update(overrides)
    return Settings(**base)


def test_the_list_is_derived_from_the_documented_variable() -> None:
    settings = _settings(cors_origins="https://a.example,https://b.example")
    assert settings.cors_origins_list == ["https://a.example", "https://b.example"]


def test_whitespace_is_stripped() -> None:
    settings = _settings(cors_origins=" https://a.example , https://b.example ")
    assert settings.cors_origins_list == ["https://a.example", "https://b.example"]


def test_a_single_origin_works() -> None:
    settings = _settings(cors_origins="https://only.example")
    assert settings.cors_origins_list == ["https://only.example"]


def test_an_empty_allowlist_is_rejected() -> None:
    """Serving with no allowed origin would break the browser client silently."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        _settings(cors_origins="   ")


def test_a_wildcard_with_credentials_is_rejected() -> None:
    """`*` plus allow_credentials=True reflects any origin with credentials."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        _settings(cors_origins="*")


def test_wildcard_is_allowed_when_credentials_are_disabled() -> None:
    """A public API may legitimately allow any origin without cookies."""
    from app.config import Settings

    settings = Settings(
        app_env="local",
        app_secret_key="",
        app_testing=True,
        cors_origins="*",
        cors_allow_credentials=False,
    )
    assert settings.cors_origins_list == ["*"]


def test_credentials_default_to_true_for_localhost() -> None:
    settings = _settings()
    assert settings.cors_allow_credentials is True

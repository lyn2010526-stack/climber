"""Default administrator account tests.

`initialize_auth_system` (app/core/auth_manager.py) created an `admin` /
`admin123` ADMIN account on every fresh deployment, unconditionally: main.py
calls it from the lifespan without consulting `enable_auth`, and the only
guard was an empty user table. The password was then printed in plaintext on
app/static/auth/login.html.

That gives a complete attack chain requiring no configuration at all, and the
account becomes a live administrator the moment `ENABLE_AUTH=true` is set.

These tests pin the fixed behaviour: production never gets a default account,
the password comes from configuration or a random value, and the login page
never advertises a credential.
"""

from __future__ import annotations

from pathlib import Path

import pytest

WEAK_PASSWORDS = {"admin123", "password", "admin", "changeme", "123456"}


def test_production_refuses_to_create_a_default_admin(monkeypatch) -> None:
    """A production deployment must not come up with a known credential."""
    from app.core import auth_manager

    monkeypatch.setattr(auth_manager.settings, "app_env", "production", raising=False)

    assert auth_manager._default_admin_allowed() is False


@pytest.mark.parametrize("environment", ["local", "development", "test", "testing"])
def test_non_production_still_allows_a_bootstrap_admin(monkeypatch, environment) -> None:
    from app.core import auth_manager

    monkeypatch.setattr(
        auth_manager.settings, "app_env", environment, raising=False
    )

    assert auth_manager._default_admin_allowed() is True


def test_a_configured_password_is_never_a_weak_default(monkeypatch) -> None:
    """An explicit password from config is used, but the weak set is rejected."""
    from app.core import auth_manager

    for weak in WEAK_PASSWORDS:
        assert auth_manager._is_acceptable_password(weak) is False, weak

    assert auth_manager._is_acceptable_password("a-real-long-passphrase") is True


def test_generated_password_is_long_and_random() -> None:
    """No configuration means a random password, not a memorable one."""
    from app.core import auth_manager

    first = auth_manager._generate_admin_password()
    second = auth_manager._generate_admin_password()

    assert len(first) >= 20
    assert first != second
    assert first.lower() not in WEAK_PASSWORDS


def test_login_page_does_not_advertise_a_default_password() -> None:
    """The login page must not print a working credential.

    Only the literal credential values are checked. The string "password"
    legitimately appears as an HTML input type and label, so matching bare
    words would fail on correct markup.
    """
    page = Path("app/static/auth/login.html")
    assert page.is_file(), "login page fixture is missing from the checkout"

    text = page.read_text(encoding="utf-8")
    for weak in ("admin123", "changeme", "change-me-in-production", "123456"):
        assert weak not in text, f"login page advertises {weak!r}"


def test_local_fallback_secret_is_not_a_repo_literal() -> None:
    """The dev fallback secret must not be a value published in the repo."""
    from app.core import auth_manager

    assert auth_manager._LOCAL_FALLBACK_SECRET != "agent-engine-local-persistent-development-key"

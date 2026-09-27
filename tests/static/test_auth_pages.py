"""Regression checks for the static login/auth browser contract."""

from pathlib import Path

STATIC_AUTH = Path(__file__).parents[2] / "app" / "static" / "auth"


def test_login_page_exposes_accessible_form_states() -> None:
    page = (STATIC_AUTH / "login.html").read_text()

    assert '<main class="login-card">' in page
    assert 'id="login-form" aria-describedby="error-alert" novalidate' in page
    assert 'id="login-status" class="visually-hidden" role="status" aria-live="polite"' in page
    assert 'loginButton.setAttribute(\'aria-busy\', \'true\')' in page
    assert 'loginButton.removeAttribute(\'aria-busy\')' in page


def test_static_auth_flow_uses_tab_scoped_token_storage() -> None:
    login_page = (STATIC_AUTH / "login.html").read_text()
    keys_page = (STATIC_AUTH / "keys.html").read_text()

    assert "sessionStorage.setItem('access_token'" in login_page
    assert "sessionStorage.getItem('access_token')" in keys_page
    assert "sessionStorage.removeItem('access_token')" in keys_page
    assert "localStorage" not in login_page
    assert "localStorage" not in keys_page


def test_login_page_rejects_malformed_success_responses() -> None:
    page = (STATIC_AUTH / "login.html").read_text()

    assert "typeof data.access_token !== 'string' || !data.access_token" in page
    assert "typeof data.detail === 'string'" in page

"""HTTP-level tests for ``/api/v1/auth/*`` in both authentication modes.

Covers the login -> token pair contract, refresh-token exchange, the identity
endpoint, and the middleware's refusal to serve a protected route without
credentials. Assertions read the real status code and the fields a client
actually depends on (token type, subject claim, identity fields).
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.core.auth_manager import create_refresh_token, hash_password, verify_token
from tests.api.conftest import admin_bearer, bearer


async def _create_user(username: str, password: str, role: str = "user") -> None:
    from app.models.users import User, UserRole, UserStatus
    from app.storage import async_session

    async with async_session() as session:
        session.add(
            User(
                username=username,
                email=f"{username}@test.local",
                hashed_password=hash_password(password),
                role=UserRole.ADMIN.value if role == "admin" else UserRole.VIEWER.value,
                status=UserStatus.ACTIVE.value,
            )
        )
        await session.commit()


# --- auth disabled -----------------------------------------------------------


async def test_login_is_rejected_while_auth_is_disabled(http) -> None:
    resp = await http.post("/api/v1/auth/login", json={"username": "u", "password": "p"})

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Authentication is disabled"


async def test_refresh_is_rejected_while_auth_is_disabled(http) -> None:
    resp = await http.post("/api/v1/auth/refresh", json={"refresh_token": "anything"})

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Authentication is disabled"


async def test_me_reports_local_identity_while_auth_is_disabled(http) -> None:
    resp = await http.get("/api/v1/auth/me")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "default-user"
    assert body["username"] == "default-user"
    assert body["role"] == "local"
    assert body["email"] == ""


async def test_auth_health_advertises_disabled_auth(http) -> None:
    resp = await http.get("/api/v1/auth/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["authentication_enabled"] is False
    assert body["auth_method"] == "disabled"
    assert body["jwt_algorithm"] == "HS256"
    assert body["token_expiry_minutes"] > 0


# --- auth enabled ------------------------------------------------------------


async def test_protected_route_requires_credentials_when_auth_enabled(http, auth_on) -> None:
    resp = await http.get("/api/v1/auth/me")

    assert resp.status_code == 401
    body = resp.json()
    assert body["type"] == "authentication_required"
    assert resp.headers["www-authenticate"] == "Bearer"


async def test_login_returns_verifiable_access_and_refresh_tokens(http, auth_on) -> None:
    await _create_user("http_login_user", "correct-horse-battery", role="admin")

    resp = await http.post(
        "/api/v1/auth/login",
        json={"username": "http_login_user", "password": "correct-horse-battery"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 60 * 60 * 24
    assert body["user"]["username"] == "http_login_user"
    assert "admin" in body["user"]["scopes"]

    access = body["access_token"]
    refresh = body["refresh_token"]
    assert verify_token(access, "access")["sub"] == body["user"]["user_id"]
    assert verify_token(refresh, "refresh")["sub"] == body["user"]["user_id"]


async def test_login_rejects_wrong_password(http, auth_on) -> None:
    await _create_user("http_wrong_pw", "correct-horse-battery")

    resp = await http.post(
        "/api/v1/auth/login", json={"username": "http_wrong_pw", "password": "nope"}
    )

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"


async def test_login_rejects_unknown_user(http, auth_on) -> None:
    resp = await http.post(
        "/api/v1/auth/login", json={"username": "ghost", "password": "whatever"}
    )

    assert resp.status_code == 401


async def test_login_gives_normal_users_their_operational_scopes(http, auth_on) -> None:
    await _create_user("http_scoped_user", "correct-horse-battery")

    resp = await http.post(
        "/api/v1/auth/login",
        json={"username": "http_scoped_user", "password": "correct-horse-battery"},
    )

    assert resp.status_code == 200
    assert resp.json()["user"]["scopes"] == ["read", "write"]
    assert verify_token(resp.json()["access_token"], "access")["scopes"] == ["read", "write"]


async def test_chat_requires_write_scope(http, auth_on) -> None:
    resp = await http.post(
        "/api/v1/sessions/missing-session/chat",
        json={"message": "hi"},
        headers=bearer("read-only", ["read"]),
    )

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Missing required scope: write"


async def test_refresh_exchanges_refresh_token_for_access_token(http, auth_on) -> None:
    await _create_user("http_refresh_user", "correct-horse-battery", role="admin")
    login = await http.post(
        "/api/v1/auth/login",
        json={"username": "http_refresh_user", "password": "correct-horse-battery"},
    )
    assert login.status_code == 200
    body = login.json()

    resp = await http.post("/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]})

    assert resp.status_code == 200
    refreshed = resp.json()
    assert refreshed["token_type"] == "bearer"
    assert refreshed["expires_in"] == 60 * 60
    claims = verify_token(refreshed["access_token"], "access")
    # The refreshed token must keep admin reach, otherwise an admin session would
    # silently degrade to a read-only caller after one refresh.
    assert "admin" in claims["scopes"]
    assert str(claims["sub"]) == str(body["user"]["user_id"])


async def test_refreshed_sub_claim_stays_a_string(http, auth_on) -> None:
    await _create_user("http_sub_type", "correct-horse-battery")
    login = await http.post(
        "/api/v1/auth/login",
        json={"username": "http_sub_type", "password": "correct-horse-battery"},
    )
    body = login.json()
    assert isinstance(verify_token(body["access_token"], "access")["sub"], str)

    resp = await http.post("/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]})

    assert resp.status_code == 200
    assert isinstance(verify_token(resp.json()["access_token"], "access")["sub"], str)


async def test_refresh_rejects_access_token(http, auth_on) -> None:
    await _create_user("http_type_user", "correct-horse-battery")
    login = await http.post(
        "/api/v1/auth/login",
        json={"username": "http_type_user", "password": "correct-horse-battery"},
    )
    access = login.json()["access_token"]

    resp = await http.post("/api/v1/auth/refresh", json={"refresh_token": access})

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Token type mismatch"


async def test_refresh_rejects_tampered_token(http, auth_on) -> None:
    resp = await http.post("/api/v1/auth/refresh", json={"refresh_token": "abc.def"})

    assert resp.status_code == 401
    assert "signature" in resp.json()["detail"].lower()


async def test_refresh_rejects_a_token_with_a_non_numeric_subject(http, auth_on) -> None:
    token = create_refresh_token("not-an-integer", ["read"])

    resp = await http.post("/api/v1/auth/refresh", json={"refresh_token": token})

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid or expired refresh token"


async def test_me_uses_bearer_identity_when_auth_enabled(http, auth_on) -> None:
    resp = await http.get("/api/v1/auth/me", headers=bearer("user-77", ["read"]))

    assert resp.status_code == 200
    body = resp.json()
    # No users row with that id exists, so the handler falls back to echoing the
    # authenticated subject rather than leaking another user's record.
    assert body["id"] == "user-77"
    assert body["role"] == "user"


async def test_me_returns_stored_profile_for_real_user(http, auth_on) -> None:
    await _create_user("http_me_user", "correct-horse-battery", role="admin")
    login = await http.post(
        "/api/v1/auth/login",
        json={"username": "http_me_user", "password": "correct-horse-battery"},
    )
    user_id = login.json()["user"]["user_id"]

    resp = await http.get("/api/v1/auth/me", headers=bearer(user_id, ["admin"]))

    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "http_me_user"
    assert body["email"] == "http_me_user@test.local"
    assert body["role"] == "admin"


async def test_logout_is_accepted_for_a_bearer_caller(http, auth_on) -> None:
    resp = await http.post("/api/v1/auth/logout", headers=admin_bearer())

    assert resp.status_code == 200
    assert resp.json()["message"] == "Logged out successfully"


async def test_auth_health_switches_auth_method_when_credentials_present(http, auth_on) -> None:
    resp = await http.get("/api/v1/auth/health", headers=admin_bearer())

    assert resp.status_code == 200
    body = resp.json()
    assert body["authentication_enabled"] is True
    # The middleware put a verified credential on request.state.
    assert body["auth_method"] == "jwt"


# --- password rotation -------------------------------------------------------


async def test_change_password_rejects_a_wrong_current_password(http, auth_on) -> None:
    await _create_user("http_pw_user", "correct-horse-battery")
    login = await http.post(
        "/api/v1/auth/login",
        json={"username": "http_pw_user", "password": "correct-horse-battery"},
    )
    user_id = login.json()["user"]["user_id"]

    resp = await http.post(
        "/api/v1/auth/change-password",
        json={"current_password": "wrong", "new_password": "another-long-secret"},
        headers=bearer(user_id),
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Current password is incorrect"


async def test_change_password_rotates_the_credential(http, auth_on) -> None:
    await _create_user("http_pw_rotate", "correct-horse-battery")
    login = await http.post(
        "/api/v1/auth/login",
        json={"username": "http_pw_rotate", "password": "correct-horse-battery"},
    )
    headers = bearer(login.json()["user"]["user_id"])

    resp = await http.post(
        "/api/v1/auth/change-password",
        json={"current_password": "correct-horse-battery", "new_password": "rotated-secret-value"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Password changed successfully"

    old = await http.post(
        "/api/v1/auth/login",
        json={"username": "http_pw_rotate", "password": "correct-horse-battery"},
    )
    new = await http.post(
        "/api/v1/auth/login",
        json={"username": "http_pw_rotate", "password": "rotated-secret-value"},
    )
    assert old.status_code == 401
    assert new.status_code == 200


async def test_change_password_404s_for_a_subject_without_a_user_row(http, auth_on) -> None:
    resp = await http.post(
        "/api/v1/auth/change-password",
        json={"current_password": "a", "new_password": "b"},
        headers=bearer("ghost-subject"),
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "User not found"


# --- scope enforcement on the API-key endpoints ------------------------------


async def test_create_api_key_requires_admin_when_auth_enabled(http, auth_on) -> None:
    """``require_scopes("admin", "write")`` demands both, so write alone is refused."""
    resp = await http.post(
        "/api/v1/auth/keys",
        json={"owner": "owner-1", "scopes": ["read"]},
        headers=bearer("plain-user", ["read", "write"]),
    )

    assert resp.status_code == 403
    assert "admin" in resp.json()["detail"]


async def test_create_api_key_is_issued_for_an_admin(http, auth_on) -> None:
    resp = await http.post(
        "/api/v1/auth/keys",
        json={"owner": "owner-1", "name": "ci", "scopes": ["read"]},
        headers=admin_bearer(),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["raw_key"].startswith("ae_")
    assert body["id"].startswith("kid_")
    assert body["scopes"] == ["read"]
    # The raw value is shown once and only the hash is stored.
    assert body["raw_key"] not in str((await http.get("/api/v1/auth/keys", headers=admin_bearer())).json())


async def test_create_api_key_is_refused_without_the_required_scopes(http, auth_on) -> None:
    resp = await http.post(
        "/api/v1/auth/keys",
        json={"owner": "owner-1", "scopes": ["read"]},
        headers=bearer("read-only-user", ["read"]),
    )

    assert resp.status_code == 403
    assert "admin" in resp.json()["detail"]


async def test_list_api_keys_requires_read_scope(http, auth_on) -> None:
    resp = await http.get("/api/v1/auth/keys", headers=bearer("write-only-user", ["write"]))

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Missing required scope: read"


async def test_revoke_api_key_requires_admin(http, auth_on) -> None:
    created = await http.post(
        "/api/v1/auth/keys",
        json={"owner": "owner-2", "name": "k"},
        headers=admin_bearer(),
    )
    assert created.status_code == 200
    key_id = created.json()["id"]

    denied = await http.delete(f"/api/v1/auth/keys/{key_id}", headers=bearer("u", ["write"]))
    assert denied.status_code == 403
    assert "admin" in denied.json()["detail"]

    missing = await http.delete("/api/v1/auth/keys/kid_does_not_exist", headers=admin_bearer())
    assert missing.status_code == 404

    allowed = await http.delete(f"/api/v1/auth/keys/{key_id}", headers=admin_bearer())
    assert allowed.status_code == 200
    assert key_id in allowed.json()["message"]


async def test_api_key_endpoints_are_disabled_while_auth_is_off(http) -> None:
    assert (await http.get("/api/v1/auth/keys")).status_code == 400
    assert (
        await http.post("/api/v1/auth/keys", json={"owner": "o"})
    ).status_code == 400


def test_refresh_rejects_expired_refresh_token() -> None:
    """A refresh token past its expiry must not verify, so a stale client cannot
    keep an access token alive forever."""
    from datetime import timedelta

    from app.core.auth_manager import create_refresh_token

    token = create_refresh_token("42", ["read"], lifetime=timedelta(seconds=-1))
    with pytest.raises(HTTPException) as exc:
        verify_token(token, "refresh")
    assert exc.value.status_code == 401
    assert "expired" in str(exc.value.detail).lower()

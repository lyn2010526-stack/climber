"""Security-layer regression tests: auth manager key/type handling, login flow,
global rate limiting, middleware JWT unification, and WebSocket ownership."""

from __future__ import annotations

import base64
import hmac
import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from app.config import settings
from app.core.auth_manager import (
    auth_manager,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_token,
)
from app.middleware.auth import _verify_jwt_token, create_jwt_token
from app.storage import async_session
from app.storage.usage import usage_tracker

OLD_DEFAULT_SECRET = "dev-secret-key-change-in-production"


def _encode_with_key(payload: dict, secret: str) -> str:
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    sig = hmac.new(secret.encode(), payload_b64.encode(), "sha256").hexdigest()[:16]
    return f"{payload_b64}.{sig}"


@pytest.fixture
def enable_auth():
    settings.enable_auth = True
    yield
    settings.enable_auth = False


# --- Bug 1: secret key case mismatch ---------------------------------------


def test_secret_reads_config_field_and_rejects_old_default() -> None:
    from app.core.auth_manager import _secret

    assert _secret() == settings.app_secret_key
    assert _secret() != OLD_DEFAULT_SECRET

    forged = _encode_with_key(
        {
            "sub": "999",
            "type": "access",
            "scopes": ["admin"],
            "iat": datetime.now(UTC).isoformat(),
            "exp": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        },
        OLD_DEFAULT_SECRET,
    )
    with pytest.raises(HTTPException) as exc_info:
        verify_token(forged, "access")
    assert exc_info.value.status_code == 401


def test_access_and_refresh_tokens_round_trip() -> None:
    access = auth_manager.create_access_token("42", ["admin"])
    refresh = auth_manager.create_refresh_token("42", ["admin"])
    assert verify_token(access, "access")["sub"] == "42"
    assert verify_token(refresh, "refresh")["sub"] == "42"


# --- Bug 2: verify_token enforces expected_type ----------------------------


def test_verify_token_rejects_wrong_type() -> None:
    access = create_access_token("42", ["user"])
    refresh = create_refresh_token("42", ["user"])

    assert verify_token(access, "access")["type"] == "access"
    assert verify_token(refresh, "refresh")["type"] == "refresh"

    with pytest.raises(HTTPException) as exc_info:
        verify_token(access, "refresh")
    assert exc_info.value.status_code == 401

    with pytest.raises(HTTPException) as exc_info:
        verify_token(refresh, "access")
    assert exc_info.value.status_code == 401


def test_verify_token_rejects_token_without_type_claim() -> None:
    from app.core.auth_manager import _secret

    typeless = _encode_with_key(
        {
            "sub": "42",
            "scopes": ["admin"],
            "iat": datetime.now(UTC).isoformat(),
            "exp": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        },
        _secret(),
    )
    with pytest.raises(HTTPException) as exc_info:
        verify_token(typeless, "access")
    assert exc_info.value.status_code == 401


# --- Bug 3: /login returns real tokens -------------------------------------


async def _create_user(username: str, password: str) -> None:
    from app.models.users import User, UserRole, UserStatus

    async with async_session() as session:
        session.add(
            User(
                username=username,
                email=f"{username}@test.local",
                hashed_password=hash_password(password),
                role=UserRole.ADMIN.value,
                status=UserStatus.ACTIVE.value,
            )
        )
        await session.commit()


async def test_login_returns_complete_token_fields(client, enable_auth) -> None:
    await _create_user("login_tester", "secret123")

    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "login_tester", "password": "secret123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    assert isinstance(body["access_token"], str) and body["access_token"]
    assert isinstance(body["refresh_token"], str) and body["refresh_token"]
    assert body["user"]["username"] == "login_tester"
    assert verify_token(body["access_token"], "access")["sub"] == body["user"]["user_id"]
    assert verify_token(body["refresh_token"], "refresh")["sub"] == body["user"]["user_id"]


async def test_login_wrong_password_rejected(client, enable_auth) -> None:
    await _create_user("login_tester2", "secret123")

    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "login_tester2", "password": "wrong-password"},
    )
    assert response.status_code == 401


async def test_refresh_endpoint_accepts_refresh_token(client, enable_auth) -> None:
    await _create_user("refresh_tester", "secret123")

    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "refresh_tester", "password": "secret123"},
    )
    assert login.status_code == 200
    refresh_token = login.json()["refresh_token"]

    refreshed = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]

    access_as_refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login.json()["access_token"]},
    )
    assert access_as_refresh.status_code == 401


# --- Bug 4: rate limiting really triggers 429 ------------------------------


async def test_usage_tracker_check_sees_recorded_requests() -> None:
    usage_tracker.reset()
    for _ in range(usage_tracker.requests_per_minute):
        await usage_tracker.record_request("rate-key")

    allowed, reason = await usage_tracker.check_rate_limit("rate-key")
    assert allowed is False
    assert reason and "Rate limit" in reason


async def test_rate_limit_middleware_returns_429(client) -> None:
    usage_tracker.reset()
    original = usage_tracker.requests_per_minute
    usage_tracker.requests_per_minute = 2
    try:
        first = await client.post("/api/v1/auth/login", json={"username": "x", "password": "y"})
        second = await client.post("/api/v1/auth/login", json={"username": "x", "password": "y"})
        assert first.status_code == 400
        assert second.status_code == 400

        third = await client.post("/api/v1/auth/login", json={"username": "x", "password": "y"})
        assert third.status_code == 429
        assert third.json()["type"] == "rate_limit_exceeded"
    finally:
        usage_tracker.requests_per_minute = original


# --- Bug 5: middleware JWT helpers share the auth_manager path -------------


def test_legacy_jwt_helpers_mutually_recognize_auth_manager_tokens() -> None:
    middleware_token = create_jwt_token("7", ["read"])
    assert verify_token(middleware_token, "access")["sub"] == "7"
    assert _verify_jwt_token(middleware_token) is not None

    manager_token = auth_manager.create_access_token("7", ["read"])
    assert _verify_jwt_token(manager_token) is not None

    assert _verify_jwt_token("garbage-token") is None


# --- Bug 6: WebSocket ownership and state cleanup --------------------------


class FakeWebSocket:
    def __init__(self, headers=None):
        self.headers = headers or {}
        self.cookies = {}
        self.closed = False
        self.close_code = None

    async def close(self, code: int = 1000) -> None:
        self.closed = True
        self.close_code = code


async def _insert_session(session_id: str, user_id: str) -> None:
    from app.storage.database import Session as SessionModel

    async with async_session() as db:
        db.add(SessionModel(id=session_id, user_id=user_id, status="pending"))
        await db.commit()


async def test_websocket_rejects_missing_and_foreign_resource(enable_auth) -> None:
    from app.api.v1.routes.websocket import _authenticate_websocket
    from app.storage.database import Session as SessionModel

    await _insert_session("owned-session", "42")
    await _insert_session("foreign-session", "99")

    access = auth_manager.create_access_token("42", ["user"])

    missing_ws = FakeWebSocket(headers={"Authorization": f"Bearer {access}"})
    result = await _authenticate_websocket(missing_ws, SessionModel, "no-such-session")
    assert result is None
    assert missing_ws.closed and missing_ws.close_code == 1008

    foreign_ws = FakeWebSocket(headers={"Authorization": f"Bearer {access}"})
    result = await _authenticate_websocket(foreign_ws, SessionModel, "foreign-session")
    assert result is None
    assert foreign_ws.closed and foreign_ws.close_code == 1008

    owned_ws = FakeWebSocket(headers={"Authorization": f"Bearer {access}"})
    result = await _authenticate_websocket(owned_ws, SessionModel, "owned-session")
    assert result == "42"
    assert not owned_ws.closed


async def test_websocket_state_dict_is_capped(monkeypatch) -> None:
    import app.api.v1.routes.websocket as ws_module

    monkeypatch.setattr(ws_module, "_MAX_WS_STATES", 3)
    states: dict[str, dict] = {}
    for i in range(5):
        ws_module._store_state(states, f"k{i}", {"i": i})

    assert len(states) == 3
    assert "k0" not in states
    assert "k1" not in states
    assert "k4" in states

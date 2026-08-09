import hashlib
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.config import settings
from app.core.auth_manager import (
    auth_manager,
    get_current_user,
    hash_password,
    require_admin,
    require_scopes,
    validate_api_key,
)
from app.models.users import ApiKey, User, UserRole, UserStatus
from app.storage import async_session
from scripts.init_admin import ensure_admin


def test_access_token_round_trip_enforces_type() -> None:
    token = auth_manager.create_access_token("42", ["read"])

    payload = auth_manager.verify_token(token, "access")

    assert payload["sub"] == "42"
    assert payload["type"] == "access"
    with pytest.raises(HTTPException, match="Invalid token type"):
        auth_manager.verify_token(token, "refresh")


def test_expired_token_is_rejected() -> None:
    token = jwt.encode(
        {
            "sub": "42",
            "type": "access",
            "exp": datetime.now(UTC) - timedelta(seconds=1),
        },
        settings.app_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(HTTPException, match="Invalid or expired token"):
        auth_manager.verify_token(token, "access")


def _request_with_auth(auth: dict) -> Request:
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
    request.state.auth = auth
    return request


@pytest.mark.asyncio
async def test_api_key_owner_username_resolves_to_active_user(monkeypatch) -> None:
    monkeypatch.setattr(settings, "enable_auth", True)
    async with async_session() as session:
        user = User(
            username="api-admin",
            email="api-admin@example.com",
            hashed_password=hash_password("correct-password"),
            role=UserRole.ADMIN.value,
            status=UserStatus.ACTIVE.value,
        )
        session.add(user)
        await session.flush()
        session.add(
            ApiKey(
                id="kid_test",
                key_hash=hashlib.sha256(b"ae_test").hexdigest(),
                owner=user.username,
                scopes='["read", "write", "admin"]',
                is_active=True,
            )
        )
        await session.commit()

    principal = await validate_api_key("ae_test")
    current_user = await get_current_user(_request_with_auth(principal or {}))

    assert current_user["username"] == "api-admin"
    assert current_user["scopes"] == ["read", "write", "admin"]


@pytest.mark.asyncio
async def test_authorization_dependencies_enforce_role_and_scopes(monkeypatch) -> None:
    monkeypatch.setattr(settings, "enable_auth", True)
    async with async_session() as session:
        user = User(
            username="viewer",
            email="viewer@example.com",
            hashed_password=hash_password("correct-password"),
            role=UserRole.VIEWER.value,
            status=UserStatus.ACTIVE.value,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    request = _request_with_auth({"sub": str(user.id), "scopes": ["read"]})

    with pytest.raises(HTTPException, match="Administrator access required"):
        await require_admin()(request)
    with pytest.raises(HTTPException, match="Insufficient scope"):
        await require_scopes("write")(request)


@pytest.mark.asyncio
async def test_disabled_auth_uses_local_admin_principal() -> None:
    request = _request_with_auth({})

    user = await require_admin()(request)

    assert user["id"] == "default-user"
    assert user["role"] == UserRole.ADMIN.value
    assert user["scopes"] == ["read", "write", "admin"]


@pytest.mark.asyncio
async def test_inactive_and_expired_api_keys_are_rejected() -> None:
    async with async_session() as session:
        user = User(
            username="key-owner",
            email="key-owner@example.com",
            hashed_password=hash_password("correct-password"),
            role=UserRole.DEVELOPER.value,
            status=UserStatus.ACTIVE.value,
        )
        session.add(user)
        await session.flush()
        session.add_all(
            [
                ApiKey(
                    id="kid_inactive",
                    key_hash=hashlib.sha256(b"ae_inactive").hexdigest(),
                    owner=user.username,
                    scopes='["read"]',
                    is_active=False,
                    created_by=user.id,
                ),
                ApiKey(
                    id="kid_expired",
                    key_hash=hashlib.sha256(b"ae_expired").hexdigest(),
                    owner=user.username,
                    scopes='["read"]',
                    is_active=True,
                    expires_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1),
                    created_by=user.id,
                ),
            ]
        )
        await session.commit()

    assert await validate_api_key("ae_inactive") is None
    assert await validate_api_key("ae_expired") is None


@pytest.mark.asyncio
async def test_admin_initialization_creates_and_updates_real_user() -> None:
    created = await ensure_admin("initial-password-123")
    updated = await ensure_admin("updated-password-456")

    assert created.id == updated.id
    assert updated.role == UserRole.ADMIN.value
    assert updated.status == UserStatus.ACTIVE.value
    assert auth_manager.verify_password("updated-password-456", updated.hashed_password)

"""Authentication manager — handles user auth, tokens, and password hashing."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import HTTPException, Request
from sqlalchemy import select

from app.config import settings
from app.models.users import ApiKey, User, UserRole, UserStatus
from app.storage import async_session


def _secret() -> str:
    return settings.app_secret_key


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return f"{salt}${h.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    if "$" not in hashed:
        return False
    salt, stored_hash = hashed.split("$", 1)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return hmac.compare_digest(h.hex(), stored_hash)


def create_token(
    user_id: str,
    scopes: list[str] | None = None,
    token_type: str = "access",
) -> str:
    now = datetime.now(UTC)
    lifetime = timedelta(minutes=settings.jwt_expire_minutes)
    if token_type == "refresh":
        lifetime = timedelta(days=7)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "scopes": scopes or [],
        "iat": now,
        "exp": now + lifetime,
    }
    return jwt.encode(payload, _secret(), algorithm=settings.jwt_algorithm)


def create_access_token(user_id: str, scopes: list[str] | None = None) -> str:
    return create_token(user_id, scopes, "access")


def create_refresh_token(user_id: str, scopes: list[str] | None = None) -> str:
    return create_token(user_id, scopes, "refresh")


def verify_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    try:
        payload = jwt.decode(token, _secret(), algorithms=[settings.jwt_algorithm])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as exc:
        raise HTTPException(401, "Invalid or expired token") from exc
    if payload.get("type") != expected_type:
        raise HTTPException(401, "Invalid token type")
    return payload


class AuthManager:
    def hash_password(self, password: str) -> str:
        return hash_password(password)

    def verify_password(self, password: str, hashed: str) -> bool:
        return verify_password(password, hashed)

    def create_access_token(self, user_id: str, scopes: list[str] | None = None) -> str:
        return create_access_token(user_id, scopes)

    def create_refresh_token(self, user_id: str, scopes: list[str] | None = None) -> str:
        return create_refresh_token(user_id, scopes)

    def verify_token(self, token: str, expected_type: str = "access") -> dict[str, Any]:
        return verify_token(token, expected_type)


auth_manager = AuthManager()


async def authenticate_user(username: str, password: str) -> dict[str, Any]:
    """Authenticate user credentials."""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.username == username, User.status == UserStatus.ACTIVE.value)
        )
        user = result.scalar_one_or_none()
        if user and verify_password(password, user.hashed_password):
            user.last_login_at = datetime.now(UTC).replace(tzinfo=None)
            await session.commit()
            scopes = ["read", "write"]
            if user.role == UserRole.ADMIN.value:
                scopes.append("admin")
            return {
                "access_token": create_access_token(str(user.id), scopes),
                "refresh_token": create_refresh_token(str(user.id), scopes),
                "expires_in": settings.jwt_expire_minutes * 60,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role,
                    "is_verified": user.is_verified,
                },
            }
    raise HTTPException(401, "Invalid credentials")


async def get_current_user(request: Request) -> dict[str, Any]:
    """Extract current user from request."""
    if not settings.enable_auth:
        return {
            "id": "default-user",
            "username": "local-user",
            "email": "",
            "full_name": "Local User",
            "role": UserRole.ADMIN.value,
            "is_verified": True,
            "scopes": ["read", "write", "admin"],
        }
    auth = getattr(request.state, "auth", None)
    if not auth or not auth.get("sub"):
        raise HTTPException(401, "Authentication required")
    try:
        user_id = int(auth["sub"])
    except (TypeError, ValueError) as exc:
        raise HTTPException(401, "Invalid authenticated user") from exc
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id, User.status == UserStatus.ACTIVE.value))
        user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(401, "User not found or inactive")
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_verified": user.is_verified,
        "scopes": auth.get("scopes", []),
    }


def require_admin():
    """Dependency that requires admin scope."""

    async def _check(request: Request):
        user = await get_current_user(request)
        if user["role"] != UserRole.ADMIN.value:
            raise HTTPException(403, "Administrator access required")
        return user

    return _check


def require_scopes(*required_scopes: str):
    """Dependency that requires specific scopes."""

    async def _check(request: Request):
        user = await get_current_user(request)
        scopes = set(user.get("scopes", []))
        if not set(required_scopes).issubset(scopes):
            raise HTTPException(403, "Insufficient scope")
        return user

    return _check


async def initialize_auth_system() -> dict[str, Any] | None:
    """Leave administrator provisioning to an explicit deployment workflow."""
    return None


async def validate_api_key(raw_key: str) -> dict[str, Any] | None:
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    async with async_session() as session:
        result = await session.execute(select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True)))
        key = result.scalar_one_or_none()
        if key is None or (key.expires_at and key.expires_at < datetime.utcnow()):
            return None
        user_query = select(User).where(User.status == UserStatus.ACTIVE.value)
        if key.created_by is not None:
            user_query = user_query.where(User.id == key.created_by)
        else:
            user_query = user_query.where(User.username == key.owner)
        user = (await session.execute(user_query)).scalar_one_or_none()
        if user is None:
            return None
        key.last_used_at = datetime.utcnow()
        await session.commit()
        return {
            "method": "api_key",
            "sub": str(user.id),
            "scopes": json.loads(key.scopes or "[]"),
            "key_id": key.id,
        }

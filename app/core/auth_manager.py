"""Authentication manager — handles user auth, tokens, and password hashing."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, Request

from app.config import settings

_LOCAL_FALLBACK_SECRET = "agent-engine-local-persistent-development-key"


def _secret() -> str:
    key = settings.app_secret_key
    if not key:
        key = _LOCAL_FALLBACK_SECRET
    return key


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


def _encode_token(payload: dict[str, Any]) -> str:
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    sig = hmac.new(_secret().encode(), payload_b64.encode(), "sha256").hexdigest()[:16]
    return f"{payload_b64}.{sig}"


def create_access_token(user_id: str, scopes: list[str] | None = None) -> str:
    payload = {
        "sub": user_id,
        "type": "access",
        "scopes": scopes or [],
        "iat": datetime.now(UTC).isoformat(),
        "exp": (datetime.now(UTC) + timedelta(hours=24)).isoformat(),
    }
    return _encode_token(payload)


def create_refresh_token(user_id: str, scopes: list[str] | None = None, lifetime: timedelta | None = None) -> str:
    payload = {
        "sub": user_id,
        "type": "refresh",
        "scopes": scopes or [],
        "iat": datetime.now(UTC).isoformat(),
        "exp": (datetime.now(UTC) + (lifetime or timedelta(days=7))).isoformat(),
    }
    return _encode_token(payload)


def verify_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    if "." not in token:
        raise HTTPException(401, "Invalid token")
    payload_b64, sig = token.rsplit(".", 1)
    expected_sig = hmac.new(_secret().encode(), payload_b64.encode(), "sha256").hexdigest()[:16]
    if not hmac.compare_digest(sig, expected_sig):
        raise HTTPException(401, "Invalid token signature")
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode()))
    except Exception:
        raise HTTPException(401, "Malformed token") from None
    exp = payload.get("exp")
    if exp:
        try:
            expires_at = datetime.fromisoformat(str(exp))
        except ValueError:
            raise HTTPException(401, "Malformed token expiry") from None
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if datetime.now(UTC) >= expires_at:
            raise HTTPException(401, "Token expired")
    if payload.get("type") != expected_type:
        raise HTTPException(401, "Token type mismatch")
    return payload


class AuthManager:
    def hash_password(self, password: str) -> str:
        return hash_password(password)

    def verify_password(self, password: str, hashed: str) -> bool:
        return verify_password(password, hashed)

    def create_access_token(self, user_id: str, scopes: list[str] | None = None) -> str:
        return create_access_token(user_id, scopes)

    def create_refresh_token(self, user_id: str, scopes: list[str] | None = None, lifetime: timedelta | None = None) -> str:
        return create_refresh_token(user_id, scopes, lifetime)

    def verify_token(self, token: str, expected_type: str = "access") -> dict[str, Any]:
        return verify_token(token, expected_type)

    @staticmethod
    def scopes_for_role(role: str | None) -> list[str]:
        return scopes_for_role(role)


auth_manager = AuthManager()


def scopes_for_role(role: str | None) -> list[str]:
    """Map a user role to the concrete authorization scopes it grants."""
    if role == "admin":
        return ["read", "write", "admin"]
    return ["read", "write"]


async def authenticate_user(username: str, password: str) -> dict[str, Any]:
    """Authenticate user credentials."""
    from sqlalchemy import select

    from app.models.users import User, UserStatus
    from app.storage import async_session
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.username == username, User.status == UserStatus.ACTIVE.value)
        )
        user = result.scalar_one_or_none()
        if user and verify_password(password, user.hashed_password):
            from datetime import datetime
            user.last_login_at = datetime.utcnow()
            await session.commit()
            return {"user_id": str(user.id), "username": user.username, "role": user.role, "scopes": scopes_for_role(user.role)}
    raise HTTPException(401, "Invalid credentials")


async def get_current_user(request: Request) -> str:
    """Extract current user id from the request-scoped principal."""
    from app.core.principal import get_context_principal

    try:
        return get_context_principal().subject_id
    except RuntimeError as exc:
        raise HTTPException(401, str(exc)) from exc


def _principal_dict() -> dict[str, Any]:
    from app.core.principal import get_context_principal

    try:
        principal = get_context_principal()
    except RuntimeError as exc:
        raise HTTPException(401, str(exc)) from exc
    return {
        "id": principal.subject_id,
        "user_id": principal.subject_id,
        "scopes": list(principal.scopes),
        "role": principal.role,
    }


def _has_scope(principal: dict[str, Any], scope: str) -> bool:
    scopes = principal.get("scopes") or []
    return "admin" in scopes or scope in scopes or principal.get("role") == scope or principal.get("role") == "admin"


def require_admin():
    """Dependency factory that rejects callers without admin scope."""
    async def _check(request: Request) -> dict[str, Any]:
        principal = _principal_dict()
        # Local mode (auth disabled) resolves to the seeded default identity.
        if not settings.enable_auth and principal["id"] == "default-user":
            return {**principal, "scopes": ["admin"], "role": "admin"}
        if principal.get("role") == "admin" or "admin" in principal["scopes"]:
            return principal
        raise HTTPException(403, "Admin scope required")
    return _check


def require_scopes(*required_scopes: str):
    """Dependency factory that enforces each required scope."""
    async def _check(request: Request) -> dict[str, Any]:
        principal = _principal_dict()
        if not settings.enable_auth and principal["id"] == "default-user":
            return {**principal, "scopes": list(required_scopes)}
        for scope in required_scopes:
            if not _has_scope(principal, scope):
                raise HTTPException(403, f"Missing required scope: {scope}")
        return principal
    return _check


async def validate_api_key(raw_key: str) -> dict[str, Any]:
    """Validate a hashed API key against the database and return auth info."""
    from sqlalchemy import select

    from app.models.users import ApiKey
    from app.storage import async_session

    if not raw_key or not raw_key.startswith("ae_"):
        raise HTTPException(401, "Invalid API key format")

    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    async with async_session() as session:
        result = await session.execute(
            select(ApiKey).where(ApiKey.key_hash == key_hash)
        )
        record = result.scalar_one_or_none()
        if record is None or not record.is_active:
            raise HTTPException(401, "Invalid API key")
        if record.expires_at is not None:
            expires = record.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=UTC)
            if datetime.now(UTC) >= expires:
                raise HTTPException(401, "API key expired")
        try:
            decoded_scopes = json.loads(record.scopes) if record.scopes else ["read", "write"]
        except (TypeError, ValueError):
            raise HTTPException(401, "Invalid API key scopes") from None
        if not isinstance(decoded_scopes, list) or not all(isinstance(scope, str) for scope in decoded_scopes):
            raise HTTPException(401, "Invalid API key scopes")
        scopes = decoded_scopes
        record.last_used_at = datetime.utcnow()
        await session.commit()

    return {
        "method": "api_key",
        "user_id": str(record.owner),
        "key_id": record.id,
        "scopes": scopes,
        "role": "admin" if "admin" in scopes else None,
    }


async def initialize_auth_system() -> dict[str, Any] | None:
    """Initialize auth system with an operator-supplied bootstrap password."""
    from sqlalchemy import func, select

    from app.models.users import User, UserRole, UserStatus
    from app.storage import async_session

    async with async_session() as session:
        result = await session.execute(select(func.count()).select_from(User))
        count = result.scalar()

        if count == 0:
            bootstrap_password = settings.initial_admin_password
            if not bootstrap_password:
                environment = settings.app_env.strip().lower()
                if environment in {"production", "prod", "staging"}:
                    raise RuntimeError("INITIAL_ADMIN_PASSWORD must be configured before first startup")
                bootstrap_password = secrets.token_urlsafe(24)
            admin = User(
                username="admin",
                email="admin@localhost",
                hashed_password=hash_password(bootstrap_password),
                role=UserRole.ADMIN.value,
                status=UserStatus.ACTIVE.value,
            )
            session.add(admin)
            await session.commit()
            return {"username": "admin", "password_set": True, "bootstrap_generated": not settings.initial_admin_password}

    return None

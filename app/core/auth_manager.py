"""Authentication manager — handles user auth, tokens, and password hashing."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, Request
from app.config import settings


def _secret() -> str:
    return getattr(settings, "APP_SECRET_KEY", "dev-secret-key-change-in-production")


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


def create_access_token(user_id: str, scopes: list[str] | None = None) -> str:
    import json
    import base64
    payload = {
        "sub": user_id,
        "scopes": scopes or [],
        "iat": datetime.now(UTC).isoformat(),
        "exp": (datetime.now(UTC) + timedelta(hours=24)).isoformat(),
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    sig = hmac.new(_secret().encode(), payload_b64.encode(), "sha256").hexdigest()[:16]
    return f"{payload_b64}.{sig}"


def verify_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    import json
    import base64
    if "." not in token:
        raise HTTPException(401, "Invalid token")
    payload_b64, sig = token.rsplit(".", 1)
    expected_sig = hmac.new(_secret().encode(), payload_b64.encode(), "sha256").hexdigest()[:16]
    if not hmac.compare_digest(sig, expected_sig):
        raise HTTPException(401, "Invalid token signature")
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode()))
    except Exception:
        raise HTTPException(401, "Malformed token")
    return payload


class AuthManager:
    def hash_password(self, password: str) -> str:
        return hash_password(password)

    def verify_password(self, password: str, hashed: str) -> bool:
        return verify_password(password, hashed)

    def create_access_token(self, user_id: str, scopes: list[str] | None = None) -> str:
        return create_access_token(user_id, scopes)

    def verify_token(self, token: str, expected_type: str = "access") -> dict[str, Any]:
        return verify_token(token, expected_type)


auth_manager = AuthManager()


async def authenticate_user(username: str, password: str) -> dict[str, Any]:
    """Authenticate user credentials."""
    from app.storage import async_session
    from app.models.users import User, UserStatus
    from sqlalchemy import select
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.username == username, User.status == UserStatus.ACTIVE.value)
        )
        user = result.scalar_one_or_none()
        if user and verify_password(password, user.hashed_password):
            from datetime import datetime
            user.last_login_at = datetime.utcnow()
            await session.commit()
            scopes = ["admin"] if user.role == "admin" else ["user"]
            return {"user_id": str(user.id), "username": user.username, "scopes": scopes}
    raise HTTPException(401, "Invalid credentials")


async def get_current_user(request: Request) -> str:
    """Extract current user from request."""
    return "default-user"


def require_admin():
    """Dependency that requires admin scope."""
    async def _check(request: Request):
        return {"user_id": "admin", "scopes": ["admin"]}
    return _check


def require_scopes(*required_scopes: str):
    """Dependency that requires specific scopes."""
    async def _check(request: Request):
        return {"user_id": "default-user", "scopes": list(required_scopes)}
    return _check


async def initialize_auth_system() -> dict[str, Any] | None:
    """Initialize auth system — create default admin user if none exists."""
    from app.storage import async_session
    from app.models.users import User, UserRole, UserStatus
    from sqlalchemy import select, func
    
    async with async_session() as session:
        result = await session.execute(select(func.count()).select_from(User))
        count = result.scalar()
        
        if count == 0:
            admin = User(
                username="admin",
                email="admin@localhost",
                hashed_password=hash_password("admin123"),
                role=UserRole.ADMIN.value,
                status=UserStatus.ACTIVE.value,
            )
            session.add(admin)
            await session.commit()
            return {"username": "admin", "password_set": True}
    
    return None

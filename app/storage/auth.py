"""Authentication & security utilities."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta
from typing import Any

import structlog
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings

logger = structlog.get_logger()
security = HTTPBearer(auto_error=False)
security_required = HTTPBearer(auto_error=True)


_fallback_fernet = None


def _get_fernet() -> Fernet:
    global _fallback_fernet
    key = getattr(settings, "app_secret_key", None)
    if not key:
        return Fernet(Fernet.generate_key())
    try:
        key_bytes = key.encode()
    except Exception:
        key_bytes = str(key).encode()
    if len(key_bytes) < 32:
        padded = key_bytes.ljust(32, b"\x00")[:32]
        return Fernet(Fernet.generate_key())
    import base64
    encoded = base64.urlsafe_b64encode(padded if len(key_bytes) < 32 else key_bytes[:32].ljust(32, b"\x00")[:32])
    return Fernet(encoded)


# ── Password hashing ──


def hash_password(password: str) -> str:
    """Hash password with salt using PBKDF2."""
    salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}${pw_hash.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Verify a password against its hash."""
    try:
        salt, hash_hex = stored.split("$", 1)
        pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
        return hmac.compare_digest(pw_hash.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False


# ── API key encryption (Fernet) ──


def encrypt_api_key(plain_key: str) -> str:
    """Encrypt an API key using Fernet symmetric encryption."""
    fernet = _get_fernet()
    return fernet.encrypt(plain_key.encode()).decode()


def decrypt_api_key(encrypted_hex: str) -> str:
    """Decrypt an API key."""
    fernet = _get_fernet()
    return fernet.decrypt(encrypted_hex.encode()).decode()


# ── JWT-like token (simple implementation) ──

def create_access_token(user_id: str, expires_hours: int = 24 * 7) -> str:
    """Create a simple signed token."""
    import json
    import base64

    payload = {
        "sub": user_id,
        "exp": (datetime.utcnow() + timedelta(hours=expires_hours)).isoformat(),
        "iat": datetime.utcnow().isoformat(),
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    signature = hmac.new(
        settings.app_secret_key.encode(),
        payload_b64.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload_b64}.{signature}"


def verify_token(token: str) -> str | None:
    """Verify a token and return user_id if valid."""
    import json
    import base64

    try:
        parts = token.split(".", 1)
        if len(parts) != 2:
            return None
        payload_b64, signature = parts
        expected_sig = hmac.new(
            settings.app_secret_key.encode(),
            payload_b64.encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None

        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        exp = datetime.fromisoformat(payload["exp"])
        if datetime.utcnow() > exp:
            return None
        return payload["sub"]
    except Exception:
        return None


# ── FastAPI dependency ──

DEFAULT_USER_ID = "default-user"

def ensure_user_id(user_id: str | None) -> str:
    """Normalize any guest/None/empty to 'default-user'."""
    if user_id and str(user_id).strip():
        return user_id
    return DEFAULT_USER_ID


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """Extract and verify current user from bearer token.

    If no token is provided, returns a default user ID so the app
    works without authentication (guest mode).
    """
    if not credentials:
        return DEFAULT_USER_ID
    user_id = verify_token(credentials.credentials)
    if not user_id:
        return DEFAULT_USER_ID
    return user_id


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """Optional auth: returns default user when no token is provided."""
    if not credentials:
        return DEFAULT_USER_ID
    user_id = verify_token(credentials.credentials)
    return user_id or DEFAULT_USER_ID


async def get_current_user_required(
    credentials: HTTPAuthorizationCredentials = Depends(security_required),
) -> str:
    """Require authentication: returns 401 if no valid token is provided."""
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


def get_current_user_ws(token: str | None) -> str | None:
    """Verify user from WebSocket query param token. Returns default user if invalid."""
    if not token:
        return DEFAULT_USER_ID
    user_id = verify_token(token)
    return user_id or DEFAULT_USER_ID

"""Production authentication middleware with database-backed API key and JWT support.

Authentication is disabled by default for backward compatibility.
Set ENABLE_AUTH=true to activate.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta

import hashlib
import json
import secrets

import jwt
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.models.users import ApiKey
from app.storage import engine

# The auth middleware validates API keys asynchronously against the same
# table; UserStore keeps a synchronous facade for the legacy test API.
# aiosqlite URLs are converted to the built-in sqlite3 driver so sync
# sessions can share the on-disk test database.
if str(engine.url).startswith("sqlite+aiosqlite"):
    _sync_url = "sqlite" + str(engine.url)[len("sqlite+aiosqlite"):]
else:
    _sync_url = str(engine.url)
_sync_engine = create_engine(
    _sync_url,
    connect_args={"check_same_thread": False, "timeout": 30},
)
_sync_session = sessionmaker(bind=_sync_engine, expire_on_commit=False)

API_KEY_HEADER = "X-API-Key"
AUTH_BEARER_PREFIX = "Bearer "
API_KEY_PREFIX = "ae_"


async def authenticate_credentials(
    headers: Mapping[str, str],
    token: str | None = None,
) -> dict | None:
    """Authenticate API key or JWT credentials from HTTP or WebSocket input."""
    api_key = headers.get(API_KEY_HEADER)
    if api_key:
        from app.core.auth_manager import validate_api_key

        return await validate_api_key(api_key)

    auth_header = headers.get("Authorization", "")
    if auth_header.startswith(AUTH_BEARER_PREFIX):
        token = auth_header[len(AUTH_BEARER_PREFIX):]

    if not token:
        return None

    from app.core.auth_manager import auth_manager

    payload = auth_manager.verify_token(token, "access")
    if not payload:
        return None

    return {
        "method": "jwt",
        "sub": payload.get("sub"),
        "scopes": payload.get("scopes", ["read", "write"]),
    }


class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware supporting API Key and JWT Bearer tokens.

    When ENABLE_AUTH is false, all requests pass through unconditionally.
    When enabled, requests to non-public endpoints must include a valid
    X-API-Key header or an Authorization: Bearer <jwt> header.

    WebSocket upgrade requests are always allowed through regardless of
    authentication status, since WebSocket authentication is handled
    separately via query params or protocol-specific mechanisms.
    """

    def __init__(self, app, public_endpoints: set[str] | None = None):
        super().__init__(app)
        self.public_endpoints: set[str] = public_endpoints or set(settings.auth_public_endpoints)

    def _is_websocket_upgrade(self, request: Request) -> bool:
        """Check if the request is a WebSocket upgrade request."""
        headers = request.headers
        connection = headers.get("connection", "").lower()
        upgrade = headers.get("upgrade", "").lower()
        return "upgrade" in connection and upgrade == "websocket"

    def _is_public_path(self, path: str) -> bool:
        """Check if path matches public patterns."""
        public_prefixes = ["/static/", "/assets/", "/favicon", "/docs", "/openapi", "/auth/health"]
        public_exact_suffixes = ("/auth/login", "/auth/refresh")
        if any(path.startswith(prefix) for prefix in public_prefixes):
            return True
        return any(path.endswith(suffix) for suffix in public_exact_suffixes)

    async def dispatch(self, request: Request, call_next):
        if not settings.enable_auth:
            request.state.auth = None
            return await call_next(request)

        if self._is_websocket_upgrade(request):
            request.state.auth = None
            return await call_next(request)

        path = request.url.path
        if path in self.public_endpoints or self._is_public_path(path):
            request.state.auth = None
            return await call_next(request)

        auth_result = await self._authenticate(request)
        if auth_result is None:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Authentication required",
                    "type": "authentication_required",
                    "hint": f"Provide {API_KEY_HEADER} header or Authorization: Bearer <token>",
                },
                headers={"WWW-Authenticate": "Bearer"},
            )

        request.state.auth = auth_result
        return await call_next(request)

    async def _authenticate(self, request: Request) -> dict | None:
        return await authenticate_credentials(request.headers)

    async def _validate_api_key(self, raw_key: str) -> dict | None:
        """Validate API key against database."""
        from app.core.auth_manager import validate_api_key

        return await validate_api_key(raw_key)

    async def _validate_jwt(self, token: str) -> dict | None:
        """Validate JWT token and return user info."""
        from app.core.auth_manager import auth_manager

        payload = auth_manager.verify_token(token, "access")
        if not payload:
            return None

        return {
            "method": "jwt",
            "sub": payload.get("sub"),
            "scopes": payload.get("scopes", ["read", "write"]),
        }


def create_jwt_token(subject: str, scopes: list[str] | None = None, expires_minutes: int | None = None) -> str:
    """Create a JWT token for the given subject."""
    now = datetime.now(UTC)
    exp_min = expires_minutes if expires_minutes is not None else settings.jwt_expire_minutes
    payload = {
        "sub": subject,
        "type": "access",
        "scopes": scopes or ["read", "write"],
        "iat": now,
        "exp": now + timedelta(minutes=exp_min),
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm=settings.jwt_algorithm)


def _verify_jwt_token(token: str) -> dict | None:
    """Verify a JWT token and return its payload, or None if invalid."""
    try:
        payload = jwt.decode(
            token,
            settings.app_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        if payload.get("type") != "access":
            return None
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def get_user_store():
    """Return the shared database-backed UserStore.

    The store persists API keys in the ``auth_api_keys`` table so that keys
    created via ``create_key`` are immediately valid for ``X-API-Key``
    authentication, matching the middleware's ``validate_api_key`` path.
    """
    global _user_store
    if _user_store is None:
        _user_store = UserStore()
    return _user_store


class UserStore:
    """Database-backed API key store.

    Keys are stored hashed (SHA-256) and validated against the same
    ``auth_api_keys`` table used by the auth middleware, keeping the legacy
    synchronous API surface while sharing production storage.
    """

    def create_key(self, owner: str, scopes: list[str] | None = None, name: str = "", ttl_days: int | None = None):
        """Create a new API key. Returns (raw_key, key_id)."""
        raw_key = API_KEY_PREFIX + secrets.token_urlsafe(32)
        key_id = "kid_" + secrets.token_hex(8)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        expires_at = None
        if ttl_days:
            expires_at = datetime.utcnow() + timedelta(days=ttl_days)

        scopes = scopes or ["read", "write"]

        with _sync_session() as session:
            record = ApiKey(
                id=key_id,
                key_hash=key_hash,
                name=name,
                owner=owner,
                scopes=json.dumps(scopes),
                is_active=True,
                expires_at=expires_at,
            )
            session.add(record)
            session.commit()

        return raw_key, key_id

    def validate_key(self, raw_key: str):
        """Validate a raw API key. Returns an entry-like object or None."""
        if not raw_key:
            return None
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        with _sync_session() as session:
            result = session.execute(
                select(ApiKey).where(
                    ApiKey.key_hash == key_hash,
                    ApiKey.is_active == True,  # noqa: E712
                )
            )
            record = result.scalar_one_or_none()
            if record is None:
                return None
            if record.expires_at and record.expires_at < datetime.utcnow():
                return None
            return record

    def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key by id. Returns True if revoked, False if missing."""
        with _sync_session() as session:
            result = session.execute(
                select(ApiKey).where(ApiKey.id == key_id)
            )
            record = result.scalar_one_or_none()
            if record is None:
                return False
            record.is_active = False
            session.commit()
            return True


_user_store: UserStore | None = None

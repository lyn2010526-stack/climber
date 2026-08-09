"""Authentication management endpoints for production."""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.config import settings
from app.core.auth_manager import (
    auth_manager,
    authenticate_user,
    get_current_user,
    require_admin,
    require_scopes,
)
from app.models.users import ApiKey, User, UserRole, UserStatus
from app.storage import async_session

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict[str, Any]


class CreateApiKeyRequest(BaseModel):
    name: str = ""
    owner: str
    scopes: list[str] | None = None
    ttl_days: int | None = None


class CreateApiKeyResponse(BaseModel):
    id: str
    raw_key: str
    name: str
    owner: str
    scopes: list[str]
    expires_at: str | None


class RevokeApiKeyRequest(BaseModel):
    key_id: str


class ListKeysResponse(BaseModel):
    keys: list[dict[str, Any]]


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UserInfoResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    is_verified: bool


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest) -> LoginResponse:
    """Login with username/password and receive JWT tokens."""
    if not settings.enable_auth:
        raise HTTPException(status_code=400, detail="Authentication is disabled")

    result = await authenticate_user(payload.username, payload.password)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return LoginResponse(**result)


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(payload: RefreshTokenRequest) -> RefreshTokenResponse:
    """Refresh an access token using a valid refresh token."""
    if not settings.enable_auth:
        raise HTTPException(status_code=400, detail="Authentication is disabled")

    payload_data = auth_manager.verify_token(payload.refresh_token, "refresh")
    if not payload_data:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user_id = int(payload_data["sub"])

    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id, User.status == UserStatus.ACTIVE.value))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found or inactive")

        scopes = ["read", "write"]
        if user.role == UserRole.ADMIN.value:
            scopes.append("admin")

    new_token = auth_manager.create_access_token(user_id, scopes)

    return RefreshTokenResponse(
        access_token=new_token,
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.post("/logout")
async def logout(request: Request) -> dict:
    """Logout and invalidate current session."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        async with async_session() as session:
            from app.models.users import UserSession

            result = await session.execute(select(UserSession).where(UserSession.token_hash == token_hash))
            user_session = result.scalar_one_or_none()
            if user_session:
                await session.delete(user_session)
                await session.commit()

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=dict)
async def get_me(current_user: dict = Depends(get_current_user)) -> dict:
    """Get current user information."""
    return current_user


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Change current user password."""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == current_user["id"]))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not auth_manager.verify_password(payload.current_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")

        user.hashed_password = auth_manager.hash_password(payload.new_password)
        await session.commit()

    return {"message": "Password changed successfully"}


@router.post("/keys", response_model=CreateApiKeyResponse)
async def create_api_key(
    payload: CreateApiKeyRequest,
    current_user: dict = Depends(require_scopes("admin", "write")),
) -> CreateApiKeyResponse:
    """Create a new API key for programmatic access."""
    if not settings.enable_auth:
        raise HTTPException(status_code=400, detail="Authentication is disabled")

    raw_key = "ae_" + secrets.token_urlsafe(32)
    key_id = "kid_" + secrets.token_hex(8)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    expires_at = None
    if payload.ttl_days:
        expires_at = datetime.utcnow() + timedelta(days=payload.ttl_days)

    scopes = payload.scopes or ["read", "write"]

    async with async_session() as session:
        api_key_record = ApiKey(
            id=key_id,
            key_hash=key_hash,
            name=payload.name,
            owner=payload.owner,
            scopes=json.dumps(scopes),
            is_active=True,
            expires_at=expires_at,
            created_by=current_user.get("id"),
        )
        session.add(api_key_record)
        await session.commit()

    return CreateApiKeyResponse(
        id=key_id,
        raw_key=raw_key,
        name=payload.name,
        owner=payload.owner,
        scopes=scopes,
        expires_at=expires_at.isoformat() if expires_at else None,
    )


@router.get("/keys", response_model=ListKeysResponse)
async def list_api_keys(
    current_user: dict = Depends(require_admin()),
) -> ListKeysResponse:
    """List all API keys."""
    if not settings.enable_auth:
        raise HTTPException(status_code=400, detail="Authentication is disabled")

    async with async_session() as session:
        result = await session.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))
        keys = result.scalars().all()

        result_keys = []
        for key in keys:
            key_scopes = json.loads(key.scopes) if key.scopes else ["read", "write"]
            result_keys.append(
                {
                    "id": key.id,
                    "name": key.name,
                    "owner": key.owner,
                    "scopes": key_scopes,
                    "is_active": key.is_active,
                    "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                    "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
                    "created_at": key.created_at.isoformat() if key.created_at else None,
                }
            )

    return ListKeysResponse(keys=result_keys)


@router.delete("/keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: dict = Depends(require_scopes("admin")),
) -> dict:
    """Revoke (deactivate) an API key."""
    if not settings.enable_auth:
        raise HTTPException(status_code=400, detail="Authentication is disabled")

    async with async_session() as session:
        result = await session.execute(select(ApiKey).where(ApiKey.id == key_id))
        key_record = result.scalar_one_or_none()
        if not key_record:
            raise HTTPException(status_code=404, detail=f"API key {key_id} not found")

        key_record.is_active = False
        await session.commit()

    return {"message": f"API key {key_id} revoked successfully"}


@router.get("/health")
async def health_check(request: Request) -> dict:
    """Check authentication system status."""
    auth_enabled = settings.enable_auth
    auth_method = "disabled"

    if auth_enabled:
        auth = getattr(request.state, "auth", None)
        if auth:
            auth_method = auth.get("method", "unknown")

    return {
        "authentication_enabled": auth_enabled,
        "auth_method": auth_method,
        "jwt_algorithm": settings.jwt_algorithm,
        "token_expiry_minutes": settings.jwt_expire_minutes,
    }

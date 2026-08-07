"""User data models with role-based access control."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.storage import Base


class UserRole(StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    DEVELOPER = "developer"
    VIEWER = "viewer"
    API = "api"


class UserStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"
    DELETED = "deleted"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(256), unique=True, nullable=False, index=True)
    hashed_password = Column(String(256), nullable=False)
    full_name = Column(String(128), default="")
    role = Column(String(32), default=UserRole.VIEWER.value, nullable=False)
    status = Column(String(32), default=UserStatus.ACTIVE.value, nullable=False)
    is_verified = Column(Boolean, default=False)
    avatar_url = Column(String(512), default="")
    preferences = Column(Text, default="{}")
    last_login_at = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    password_changed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    token_hash = Column(String(128), unique=True, nullable=False)
    refresh_token_hash = Column(String(128), unique=True, nullable=True)
    ip_address = Column(String(64), default="")
    user_agent = Column(String(512), default="")
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserInvitation(Base):
    __tablename__ = "user_invitations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(256), nullable=False, index=True)
    token_hash = Column(String(128), unique=True, nullable=False)
    invited_by = Column(Integer, nullable=False)
    role = Column(String(32), default=UserRole.VIEWER.value)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserActivity(Base):
    __tablename__ = "user_activities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    action = Column(String(64), nullable=False)
    resource_type = Column(String(64), default="")
    resource_id = Column(String(128), default="")
    ip_address = Column(String(64), default="")
    user_agent = Column(String(512), default="")
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    key = Column(String(128), nullable=False)
    value = Column(Text, default="")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ApiKey(Base):
    __tablename__ = "auth_api_keys"

    id = Column(String(64), primary_key=True)
    key_hash = Column(String(128), unique=True, nullable=False, index=True)
    name = Column(String(128), default="")
    owner = Column(String(64), nullable=False, index=True)
    scopes = Column(Text, default='["read", "write"]')
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, nullable=True)


# --- Pydantic schemas ---

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = ""
    role: UserRole = UserRole.VIEWER


class UserUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    role: UserRole | None = None
    status: UserStatus | None = None
    avatar_url: str | None = None
    preferences: dict[str, Any] | None = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: UserRole
    status: UserStatus
    is_verified: bool
    avatar_url: str
    last_login_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int
    page: int
    page_size: int


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class BulkUserCreate(BaseModel):
    users: list[UserCreate]


class UserRoleUpdate(BaseModel):
    role: UserRole


class UserStatusUpdate(BaseModel):
    status: UserStatus
    reason: str = ""


class ApiKeyCreate(BaseModel):
    name: str = ""
    owner: str
    scopes: list[str] | None = None
    ttl_days: int | None = None


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    owner: str
    scopes: list[str]
    is_active: bool
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class ApiKeyCreatedResponse(BaseModel):
    id: str
    raw_key: str
    name: str
    owner: str
    scopes: list[str]
    expires_at: datetime | None

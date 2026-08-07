#!/usr/bin/env python3
"""Generator for user management module: models, schemas, API routes, services, tests."""

from pathlib import Path

BASE = Path("/workspace/agent-engine")
MODELS_DIR = BASE / "app" / "models" / "user_management"
SCHEMAS_DIR = BASE / "app" / "schemas" / "user_management"
API_DIR = BASE / "app" / "api" / "v1" / "user_management"
SERVICES_DIR = BASE / "app" / "services" / "user_management"
TESTS_DIR = BASE / "tests" / "modules" / "user_management"

for d in [MODELS_DIR, SCHEMAS_DIR, API_DIR, SERVICES_DIR, TESTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Models ──

def generate_user_model():
    return '''"""User management data models.

This module defines SQLAlchemy ORM models for user management including
user accounts, roles, permissions, sessions, and audit trails.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Enum as SAEnum, Float, ForeignKey,
    Index, Integer, String, Table, Text, UniqueConstraint, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.storage.database import Base


class UserStatus(str, Enum):
    """User account status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"
    LOCKED = "locked"
    DELETED = "deleted"


class UserRole(str, Enum):
    """User role enumeration for RBAC."""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"
    VIEWER = "viewer"
    GUEST = "guest"


class PermissionScope(str, Enum):
    """Permission scope enumeration."""
    GLOBAL = "global"
    ORGANIZATION = "organization"
    PROJECT = "project"
    RESOURCE = "resource"


class MFAMethod(str, Enum):
    """Multi-factor authentication method."""
    NONE = "none"
    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"
    HARDWARE_KEY = "hardware_key"


class User(Base):
    """User account model representing an authenticated entity.

    Stores core user information including credentials, profile data,
    security settings, and account status.

    Attributes:
        id: Unique identifier (UUID).
        email: Unique email address used for authentication.
        username: Unique username for display and login.
        hashed_password: Bcrypt-hashed password.
        full_name: User's full display name.
        avatar_url: URL to user's avatar image.
        status: Current account status.
        role: Primary role for RBAC.
        mfa_method: Enabled MFA method.
        mfa_secret: Encrypted MFA secret key.
        email_verified: Whether email has been verified.
        phone_number: Optional phone number for SMS MFA.
        phone_verified: Whether phone has been verified.
        last_login_at: Timestamp of last successful login.
        last_login_ip: IP address of last login.
        failed_login_count: Consecutive failed login attempts.
        locked_until: Account lockout expiry timestamp.
        password_changed_at: When password was last changed.
        must_change_password: Force password change on next login.
        locale: User's preferred language/locale.
        timezone: User's preferred timezone.
        metadata_json: Additional metadata as JSON.
        created_at: Account creation timestamp.
        updated_at: Last update timestamp.
        deleted_at: Soft delete timestamp.
    """

    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_username", "username"),
        Index("ix_users_status", "status"),
        Index("ix_users_role", "role"),
        Index("ix_users_created_at", "created_at"),
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("username", name="uq_users_username"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    status: Mapped[UserStatus] = mapped_column(SAEnum(UserStatus), default=UserStatus.PENDING_VERIFICATION, nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.MEMBER, nullable=False)
    mfa_method: Mapped[MFAMethod] = mapped_column(SAEnum(MFAMethod), default=MFAMethod.NONE, nullable=False)
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    phone_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    locale: Mapped[str] = mapped_column(String(16), default="en", nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    sessions: Mapped[list["UserSession"]] = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    permissions: Mapped[list["UserPermission"]] = relationship("UserPermission", back_populates="user", cascade="all, delete-orphan")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user")
    login_history: Mapped[list["LoginHistory"]] = relationship("LoginHistory", back_populates="user", cascade="all, delete-orphan")
    api_keys: Mapped[list["UserApiKey"]] = relationship("UserApiKey", back_populates="user", cascade="all, delete-orphan")
    organizations: Mapped[list["OrganizationMember"]] = relationship("OrganizationMember", back_populates="user")
    notifications: Mapped[list["UserNotification"]] = relationship("UserNotification", back_populates="user", cascade="all, delete-orphan")
    preferences: Mapped[list["UserPreference"]] = relationship("UserPreference", back_populates="user", cascade="all, delete-orphan")

    @property
    def is_active(self) -> bool:
        """Check if user account is active."""
        return self.status == UserStatus.ACTIVE

    @property
    def is_locked(self) -> bool:
        """Check if account is currently locked."""
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until

    @property
    def display_name(self) -> str:
        """Get display name (full name or username)."""
        return self.full_name or self.username

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


class UserSession(Base):
    """User session model for tracking active authentication sessions.

    Attributes:
        id: Session identifier.
        user_id: Associated user ID.
        token_hash: Hashed session token for validation.
        refresh_token_hash: Hashed refresh token.
        ip_address: IP address where session was created.
        user_agent: User agent string of the client.
        device_fingerprint: Optional device fingerprint.
        expires_at: Session expiration timestamp.
        refresh_expires_at: Refresh token expiration.
        is_active: Whether session is still valid.
        revoked_at: When session was revoked.
        created_at: Session creation timestamp.
        last_activity_at: Last activity timestamp.
    """

    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("ix_user_sessions_user_id", "user_id"),
        Index("ix_user_sessions_token_hash", "token_hash"),
        Index("ix_user_sessions_expires_at", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    refresh_token_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    device_fingerprint: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    refresh_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="sessions")

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        return self.is_active and not self.is_expired and self.revoked_at is None


class Role(Base):
    """Role definition for RBAC system.

    Attributes:
        id: Role identifier.
        name: Unique role name.
        description: Role description.
        permissions: List of permission strings.
        is_system: Whether this is a system-defined role.
        is_active: Whether role is currently usable.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "roles"
    __table_args__ = (
        Index("ix_roles_name", "name"),
        UniqueConstraint("name", name="uq_roles_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    permissions: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user_assignments: Mapped[list["UserRoleAssignment"]] = relationship("UserRoleAssignment", back_populates="role", cascade="all, delete-orphan")


class Permission(Base):
    """Permission definition for fine-grained access control.

    Attributes:
        id: Permission identifier.
        code: Unique permission code (e.g., 'users:read').
        name: Human-readable name.
        description: Detailed description.
        scope: Permission scope level.
        resource_type: Type of resource this applies to.
        actions: List of allowed actions.
        conditions: Optional conditions as JSON.
        is_system: Whether this is a system permission.
        created_at: Creation timestamp.
    """

    __tablename__ = "permissions"
    __table_args__ = (
        Index("ix_permissions_code", "code"),
        Index("ix_permissions_scope", "scope"),
        UniqueConstraint("code", name="uq_permissions_code"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    scope: Mapped[PermissionScope] = mapped_column(SAEnum(PermissionScope), default=PermissionScope.RESOURCE, nullable=False)
    resource_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    actions: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    conditions: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserRoleAssignment(Base):
    """Mapping between users and roles.

    Attributes:
        id: Assignment identifier.
        user_id: User ID.
        role_id: Role ID.
        assigned_by: User ID who made the assignment.
        expires_at: Optional expiration for temporary roles.
        created_at: Assignment timestamp.
    """

    __tablename__ = "user_role_assignments"
    __table_args__ = (
        Index("ix_user_role_assignments_user_id", "user_id"),
        Index("ix_user_role_assignments_role_id", "role_id"),
        UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    assigned_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User")
    role: Mapped["Role"] = relationship("Role", back_populates="user_assignments")


class UserPermission(Base):
    """Direct permission assignment to users (overrides role permissions).

    Attributes:
        id: Assignment identifier.
        user_id: User ID.
        permission_id: Permission ID.
        granted: Whether permission is granted or denied.
        expires_at: Optional expiration.
        created_at: Assignment timestamp.
    """

    __tablename__ = "user_permissions"
    __table_args__ = (
        Index("ix_user_permissions_user_id", "user_id"),
        UniqueConstraint("user_id", "permission_id", name="uq_user_permission"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    permission_id: Mapped[str] = mapped_column(String(36), ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="permissions")
    permission: Mapped["Permission"] = relationship("Permission")


class LoginHistory(Base):
    """Record of user login attempts for security auditing.

    Attributes:
        id: Record identifier.
        user_id: User ID.
        ip_address: Source IP address.
        user_agent: Client user agent.
        success: Whether login was successful.
        failure_reason: Reason for failed login.
        mfa_used: Whether MFA was used.
        geo_location: Geolocation data as JSON.
        created_at: Attempt timestamp.
    """

    __tablename__ = "login_history"
    __table_args__ = (
        Index("ix_login_history_user_id", "user_id"),
        Index("ix_login_history_created_at", "created_at"),
        Index("ix_login_history_ip", "ip_address"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    mfa_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    geo_location: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="login_history")


class UserApiKey(Base):
    """API key for programmatic access.

    Attributes:
        id: Key identifier.
        user_id: Owner user ID.
        name: Human-readable key name.
        key_prefix: First 8 chars for identification.
        key_hash: Full key hash for validation.
        scopes: List of permission scopes.
        rate_limit: Requests per minute limit.
        last_used_at: Last usage timestamp.
        expires_at: Optional expiration.
        is_active: Whether key is active.
        created_at: Creation timestamp.
    """

    __tablename__ = "user_api_keys"
    __table_args__ = (
        Index("ix_user_api_keys_user_id", "user_id"),
        Index("ix_user_api_keys_key_prefix", "key_prefix"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    scopes: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    rate_limit: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="api_keys")


class PasswordResetToken(Base):
    """Token for password reset flow.

    Attributes:
        id: Token identifier.
        user_id: Associated user ID.
        token_hash: Hashed reset token.
        expires_at: Token expiration.
        used_at: When token was consumed.
        created_at: Creation timestamp.
    """

    __tablename__ = "password_reset_tokens"
    __table_args__ = (
        Index("ix_password_reset_tokens_user_id", "user_id"),
        Index("ix_password_reset_tokens_token_hash", "token_hash"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    @property
    def is_valid(self) -> bool:
        return self.used_at is None and datetime.utcnow() < self.expires_at


class EmailVerificationToken(Base):
    """Token for email verification.

    Attributes:
        id: Token identifier.
        user_id: Associated user ID.
        email: Email being verified.
        token_hash: Hashed verification token.
        expires_at: Token expiration.
        verified_at: When email was verified.
        created_at: Creation timestamp.
    """

    __tablename__ = "email_verification_tokens"
    __table_args__ = (
        Index("ix_email_verification_tokens_user_id", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserPreference(Base):
    """User-specific preferences and settings.

    Attributes:
        id: Preference identifier.
        user_id: Associated user ID.
        category: Preference category.
        key: Preference key.
        value: Preference value as JSON.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "user_preferences"
    __table_args__ = (
        Index("ix_user_preferences_user_id", "user_id"),
        UniqueConstraint("user_id", "category", "key", name="uq_user_preference"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="preferences")


class UserNotification(Base):
    """User notification model.

    Attributes:
        id: Notification identifier.
        user_id: Recipient user ID.
        type: Notification type.
        title: Notification title.
        message: Notification body.
        data: Additional data as JSON.
        read: Whether notification has been read.
        read_at: When notification was read.
        created_at: Creation timestamp.
    """

    __tablename__ = "user_notifications"
    __table_args__ = (
        Index("ix_user_notifications_user_id", "user_id"),
        Index("ix_user_notifications_created_at", "created_at"),
        Index("ix_user_notifications_read", "read"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="notifications")
'''

# Write models
(MODELS_DIR / "__init__.py").write_text('"""User management models package."""\n')
(MODELS_DIR / "user.py").write_text(generate_user_model())

print("Generated user management models")

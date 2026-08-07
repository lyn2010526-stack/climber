#!/usr/bin/env python3
"""Generate extensive backend modules for agent-engine expansion."""

from __future__ import annotations

import textwrap
from pathlib import Path

BASE = Path("/workspace/agent-engine")
MODULES_DIR = BASE / "app" / "generated"


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ============================================================
# 1. Generate comprehensive user management module
# ============================================================
def generate_user_management():
    modules = {}

    # --- models/users.py ---
    modules["app/models/users.py"] = textwrap.dedent('''\
        """User data models with role-based access control."""

        from __future__ import annotations

        from datetime import datetime
        from enum import Enum
        from typing import Any, Optional

        from pydantic import BaseModel, EmailStr, Field
        from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
        from sqlalchemy.orm import declarative_base

        Base = declarative_base()


        class UserRole(str, Enum):
            ADMIN = "admin"
            MANAGER = "manager"
            DEVELOPER = "developer"
            VIEWER = "viewer"
            API = "api"


        class UserStatus(str, Enum):
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
    ''')

    # --- services/user_service.py ---
    modules["app/services/user_service.py"] = textwrap.dedent('''\
        """User management service with authentication and authorization."""

        from __future__ import annotations

        import hashlib
        import hmac
        import secrets
        from datetime import datetime, timedelta
        from typing import Any, Optional

        import jwt
        import structlog
        from sqlalchemy import select, update, func
                from sqlalchemy.ext.asyncio import AsyncSession

        from app.config import settings
        from app.models.users import (
            LoginResponse,
            User,
            UserActivity,
            UserCreate,
            UserInvitation,
            UserResponse,
            UserRole,
            UserSession,
            UserStatus,
            UserUpdate,
        )

        logger = structlog.get_logger()

        ALGORITHM = "HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES = 60
        REFRESH_TOKEN_EXPIRE_DAYS = 30
        MAX_FAILED_ATTEMPTS = 5
        LOCKOUT_DURATION_MINUTES = 30


        class UserService:
            """Comprehensive user management service."""

            def __init__(self, session: AsyncSession):
                self.session = session

            async def create_user(self, data: UserCreate, created_by: int | None = None) -> UserResponse:
                """Create a new user account."""
                existing = await self.session.execute(
                    select(User).where((User.username == data.username) | (User.email == data.email))
                )
                if existing.scalar_one_or_none():
                    raise ValueError("Username or email already exists")

                user = User(
                    username=data.username,
                    email=data.email,
                    hashed_password=self._hash_password(data.password),
                    full_name=data.full_name,
                    role=data.role.value,
                    status=UserStatus.ACTIVE.value,
                )
                self.session.add(user)
                await self.session.flush()

                if created_by:
                    await self._log_activity(user.id, "user.created", "user", str(user.id), created_by)

                await self.session.commit()
                return UserResponse.model_validate(user)

            async def authenticate(self, username: str, password: str) -> LoginResponse | None:
                """Authenticate user and return tokens."""
                result = await self.session.execute(
                    select(User).where(User.username == username)
                )
                user = result.scalar_one_or_none()
                if not user or not self._verify_password(password, user.hashed_password):
                    if user:
                        user.failed_login_attempts += 1
                        await self.session.commit()
                    return None

                if user.status != UserStatus.ACTIVE.value:
                    return None

                if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                    lockout_time = datetime.utcnow() - timedelta(minutes=LOCKOUT_DURATION_MINUTES)
                    if user.last_login_at and user.last_login_at > lockout_time:
                        return None
                    user.failed_login_attempts = 0

                user.failed_login_attempts = 0
                user.last_login_at = datetime.utcnow()
                await self.session.commit()

                access_token = self._create_token(user.id, "access", ACCESS_TOKEN_EXPIRE_MINUTES)
                refresh_token = self._create_token(user.id, "refresh", REFRESH_TOKEN_EXPIRE_DAYS * 1440)

                session = UserSession(
                    user_id=user.id,
                    token_hash=self._hash_token(access_token),
                    refresh_token_hash=self._hash_token(refresh_token),
                    expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
                )
                self.session.add(session)
                await self.session.commit()

                return LoginResponse(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                    user=UserResponse.model_validate(user),
                )

            async def get_user(self, user_id: int) -> User | None:
                """Get user by ID."""
                result = await self.session.execute(select(User).where(User.id == user_id))
                return result.scalar_one_or_none()

            async def list_users(
                self, page: int = 1, page_size: int = 20, role: str | None = None, status: str | None = None
            ) -> tuple[list[User], int]:
                """List users with pagination and filters."""
                query = select(User)
                count_query = select(func.count()).select_from(User)

                if role:
                    query = query.where(User.role == role)
                    count_query = count_query.where(User.role == role)
                if status:
                    query = query.where(User.status == status)
                    count_query = count_query.where(User.status == status)

                query = query.offset((page - 1) * page_size).limit(page_size)
                query = query.order_by(User.created_at.desc())

                result = await self.session.execute(query)
                count_result = await self.session.execute(count_query)

                return result.scalars().all(), count_result.scalar()

            async def update_user(self, user_id: int, data: UserUpdate) -> User | None:
                """Update user profile."""
                user = await self.get_user(user_id)
                if not user:
                    return None

                update_data = {}
                if data.full_name is not None:
                    update_data["full_name"] = data.full_name
                if data.email is not None:
                    update_data["email"] = data.email
                if data.role is not None:
                    update_data["role"] = data.role.value
                if data.status is not None:
                    update_data["status"] = data.status.value
                if data.avatar_url is not None:
                    update_data["avatar_url"] = data.avatar_url
                if data.preferences is not None:
                    import json
                    update_data["preferences"] = json.dumps(data.preferences)

                if update_data:
                    update_data["updated_at"] = datetime.utcnow()
                    await self.session.execute(update(User).where(User.id == user_id).values(**update_data))
                    await self.session.commit()
                    return await self.get_user(user_id)
                return user

            async def delete_user(self, user_id: int, hard: bool = False) -> bool:
                """Soft or hard delete a user."""
                user = await self.get_user(user_id)
                if not user:
                    return False

                if hard:
                    await self.session.delete(user)
                else:
                    user.status = UserStatus.DELETED.value
                    user.deleted_at = datetime.utcnow()
                await self.session.commit()
                return True

            async def change_password(self, user_id: int, current: str, new: str) -> bool:
                """Change user password."""
                user = await self.get_user(user_id)
                if not user or not self._verify_password(current, user.hashed_password):
                    return False
                user.hashed_password = self._hash_password(new)
                user.password_changed_at = datetime.utcnow()
                await self.session.commit()
                return True

            async def refresh_access_token(self, refresh_token: str) -> tuple[str, int] | None:
                """Generate new access token from refresh token."""
                payload = self._decode_token(refresh_token)
                if not payload or payload.get("type") != "refresh":
                    return None

                token_hash = self._hash_token(refresh_token)
                result = await self.session.execute(
                    select(UserSession).where(UserSession.refresh_token_hash == token_hash)
                )
                session = result.scalar_one_or_none()
                if not session or session.expires_at < datetime.utcnow():
                    return None

                new_access = self._create_token(session.user_id, "access", ACCESS_TOKEN_EXPIRE_MINUTES)
                return new_access, ACCESS_TOKEN_EXPIRE_MINUTES * 60

            async def verify_token(self, token: str) -> dict[str, Any] | None:
            """Verify and decode access token."""
                payload = self._decode_token(token)
                if not payload or payload.get("type") != "access":
                    return None
                return payload

            async def revoke_token(self, token: str) -> bool:
                """Revoke a user session token."""
                token_hash = self._hash_token(token)
                result = await self.session.execute(
                    select(UserSession).where(UserSession.token_hash == token_hash)
                )
                session = result.scalar_one_or_none()
                if session:
                    await self.session.delete(session)
                    await self.session.commit()
                    return True
                return False

            async def revoke_all_user_tokens(self, user_id: int) -> int:
                """Revall all tokens for a user."""
                result = await self.session.execute(
                    select(UserSession).where(UserSession.user_id == user_id)
                )
                sessions = result.scalars().all()
                count = len(sessions)
                for s in sessions:
                    await self.session.delete(s)
                await self.session.commit()
                return count

            async def create_invitation(self, email: str, invited_by: int, role: UserRole) -> UserInvitation:
                """Create user invitation."""
                token = secrets.token_urlsafe(48)
                invitation = UserInvitation(
                    email=email,
                    token_hash=self._hash_token(token),
                    invited_by=invited_by,
                    role=role.value,
                    expires_at=datetime.utcnow() + timedelta(days=7),
                )
                self.session.add(invitation)
                await self.session.commit()
                return invitation

            async def accept_invitation(self, token: str, password: str) -> User | None:
                """Accept invitation and create user account."""
                token_hash = self._hash_token(token)
                result = await self.session.execute(
                    select(UserInvitation).where(UserInvitation.token_hash == token_hash)
                )
                invitation = result.scalar_one_or_none()
                if not invitation or invitation.expires_at < datetime.utcnow() or invitation.accepted_at:
                    return None

                user = User(
                    username=invitation.email.split("@")[0],
                    email=invitation.email,
                    hashed_password=self._hash_password(password),
                    role=invitation.role,
                    status=UserStatus.ACTIVE.value,
                    is_verified=True,
                )
                self.session.add(user)
                invitation.accepted_at = datetime.utcnow()
                await self.session.commit()
                return user

            async def _log_activity(
                self, user_id: int, action: str, resource_type: str, resource_id: str, actor_id: int
            ) -> None:
                """Log user activity for audit trail."""
                activity = UserActivity(
                    user_id=user_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                )
                self.session.add(activity)

            def _hash_password(self, password: str) -> str:
                """Hash password using SHA-256 with salt."""
                salt = secrets.token_hex(16)
                pw_hash = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
                return f"{salt}${pw_hash}"

            def _verify_password(self, password: str, hashed: str) -> bool:
                """Verify password against hash."""
                if "$" not in hashed:
                    return False
                salt, stored_hash = hashed.split("$", 1)
                pw_hash = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
                return hmac.compare_digest(pw_hash, stored_hash)

            def _create_token(self, user_id: int, token_type: str, expire_minutes: int) -> str:
                """Create JWT token."""
                now = datetime.utcnow()
                payload = {
                    "sub": str(user_id),
                    "type": token_type,
                    "iat": now,
                    "exp": now + timedelta(minutes=expire_minutes),
                    "jti": secrets.token_hex(16),
                }
                return jwt.encode(payload, settings.app_secret_key, algorithm=ALGORITHM)

            def _decode_token(self, token: str) -> dict[str, Any] | None:
                """Decode and verify JWT token."""
                try:
                    return jwt.decode(token, settings.app_secret_key, algorithms=[ALGORITHM])
                except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
                    return None

            def _hash_token(self, token: str) -> str:
                """Hash a token for storage."""
                return hashlib.sha256(token.encode()).hexdigest()
    ''')

    # --- api/v1/users.py (enhanced) ---
    modules["app/api/v1/users.py"] = textwrap.dedent('''\
        """User management API endpoints."""

        from __future__ import annotations

        from fastapi import APIRouter, Depends, HTTPException, Query, status
        from sqlalchemy.ext.asyncio import AsyncSession

        from app.models.users import (
            LoginRequest,
            LoginResponse,
            PasswordChangeRequest,
            PasswordResetConfirm,
            PasswordResetRequest,
            UserCreate,
            UserResponse,
            UserRole,
            UserRoleUpdate,
            UserStatus,
            UserStatusUpdate,
            UserUpdate,
        )
        from app.services.user_service import UserService
        from app.storage.database import get_db

        router = APIRouter()


        async def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
            return UserService(db)


        @router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
        async def register_user(
            data: UserCreate,
            service: UserService = Depends(get_user_service),
        ) -> UserResponse:
            """Register a new user account."""
            try:
                return await service.create_user(data)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))


        @router.post("/login", response_model=LoginResponse)
        async def login(
            data: LoginRequest,
            service: UserService = Depends(get_user_service),
        ) -> LoginResponse:
            """Authenticate and receive access token."""
            result = await service.authenticate(data.username, data.password)
            if not result:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            return result


        @router.post("/refresh")
        async def refresh_token(
            data: dict,
            service: UserService = Depends(get_user_service),
        ) -> dict:
            """Refresh access token."""
            refresh_token_value = data.get("refresh_token", "")
            result = await service.refresh_access_token(refresh_token_value)
            if not result:
                raise HTTPException(status_code=401, detail="Invalid refresh token")
            access_token, expires_in = result
            return {"access_token": access_token, "expires_in": expires_in}


        @router.get("/me", response_model=UserResponse)
        async def get_current_user(
            token_data: dict = Depends(lambda: {}),
            service: UserService = Depends(get_user_service),
        ) -> UserResponse:
            """Get current authenticated user."""
            user_id = int(token_data.get("sub", 0))
            user = await service.get_user(user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            return UserResponse.model_validate(user)


        @router.get("/", response_model=list[UserResponse])
        async def list_users(
            page: int = Query(1, ge=1),
            page_size: int = Query(20, ge=1, le=100),
            role: UserRole | None = None,
            status: UserStatus | None = None,
            service: UserService = Depends(get_user_service),
        ) -> list[UserResponse]:
            """List all users with pagination."""
            users, _ = await service.list_users(page, page_size, role, status)
            return [UserResponse.model_validate(u) for u in users]


        @router.get("/{user_id}", response_model=UserResponse)
        async def get_user(
            user_id: int,
            service: UserService = Depends(get_user_service),
        ) -> UserResponse:
            """Get user by ID."""
            user = await service.get_user(user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            return UserResponse.model_validate(user)


        @router.patch("/{user_id}", response_model=UserResponse)
        async def update_user(
            user_id: int,
            data: UserUpdate,
            service: UserService = Depends(get_user_service),
        ) -> UserResponse:
            """Update user profile."""
            user = await service.update_user(user_id, data)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            return UserResponse.model_validate(user)


        @router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
        async def delete_user(
            user_id: int,
            hard: bool = Query(False),
            service: UserService = Depends(get_user_service),
        ) -> None:
            """Delete a user."""
            deleted = await service.delete_user(user_id, hard)
            if not deleted:
                raise HTTPException(status_code=404, detail="User not found")


        @router.post("/{user_id}/change-password")
        async def change_password(
            user_id: int,
            data: PasswordChangeRequest,
            service: UserService = Depends(get_user_service),
        ) -> dict:
            """Change user password."""
            success = await service.change_password(user_id, data.current_password, data.new_password)
            if not success:
                raise HTTPException(status_code=400, detail="Invalid current password")
            return {"message": "Password changed successfully"}


        @router.patch("/{user_id}/role", response_model=UserResponse)
        async def update_user_role(
            user_id: int,
            data: UserRoleUpdate,
            service: UserService = Depends(get_user_service),
        ) -> UserResponse:
            """Update user role."""
            user = await service.update_user(user_id, UserUpdate(role=data.role))
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            return UserResponse.model_validate(user)


        @router.patch("/{user_id}/status", response_model=UserResponse)
        async def update_user_status(
            user_id: int,
            data: UserStatusUpdate,
            service: UserService = Depends(get_user_service),
        ) -> UserResponse:
            """Update user status."""
            user = await service.update_user(user_id, UserUpdate(status=data.status))
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            return UserResponse.model_validate(user)


        @router.post("/{user_id}/revoke-sessions")
        async def revoke_user_sessions(
            user_id: int,
            service: UserService = Depends(get_user_service),
        ) -> dict:
            """Revoke all sessions for a user."""
            count = await service.revoke_all_user_tokens(user_id)
            return {"revoked": count}


        @router.post("/invite", status_code=status.HTTP_201_CREATED)
        async def invite_user(
            email: str,
            role: UserRole = UserRole.VIEWER,
            service: UserService = Depends(get_user_service),
        ) -> dict:
            """Invite a new user."""
            invitation = await service.create_invitation(email, 0, role)
            return {"message": "Invitation sent", "invitation_id": invitation.id}


        @router.post("/accept-invitation", response_model=UserResponse)
        async def accept_invitation(
            token: str,
            password: str,
            service: UserService = Depends(get_user_service),
        ) -> UserResponse:
            """Accept invitation and create account."""
            user = await service.accept_invitation(token, password)
            if not user:
                raise HTTPException(status_code=400, detail="Invalid or expired invitation")
            return UserResponse.model_validate(user)
    ''')

    return modules


# ============================================================
# 2. Generate permissions and RBAC module
# ============================================================
def generate_permissions_module():
    modules = {}

    # --- models/permissions.py ---
    modules["app/models/permissions.py"] = textwrap.dedent('''\
        """Permission and role-based access control models."""

        from __future__ import annotations

        from datetime import datetime
        from enum import Enum
        from typing import Any, Optional

        from pydantic import BaseModel, Field
        from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text, UniqueConstraint
        from sqlalchemy.orm import declarative_base, relationship

        Base = declarative_base()


        class PermissionScope(str, Enum):
            GLOBAL = "global"
            WORKSPACE = "workspace"
            PROJECT = "project"
            RESOURCE = "resource"


        class PermissionEffect(str, Enum):
            ALLOW = "allow"
            DENY = "deny"


        class ResourceType(str, Enum):
            AGENT = "agent"
            SESSION = "session"
            DOCUMENT = "document"
            WORKFLOW = "workflow"
            TOOL = "tool"
            SKILL = "skill"
            GROUP = "group"
            USER = "user"
            BILLING = "billing"
            SETTINGS = "settings"


        class Action(str, Enum):
            CREATE = "create"
            READ = "read"
            UPDATE = "update"
            DELETE = "delete"
            EXECUTE = "execute"
            MANAGE = "manage"
            SHARE = "share"
            EXPORT = "export"
            ADMIN = "admin"


        class RoleDefinition(Base):
            __tablename__ = "role_definitions"

            id = Column(Integer, primary_key=True, autoincrement=True)
            name = Column(String(64), unique=True, nullable=False, index=True)
            description = Column(String(512), default="")
            is_system = Column(Boolean, default=False)
            priority = Column(Integer, default=0)
            metadata_json = Column(Text, default="{}")
            created_at = Column(DateTime, default=datetime.utcnow)
            updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


        class Permission(Base):
            __tablename__ = "permissions"

            id = Column(Integer, primary_key=True, autoincrement=True)
            role_id = Column(Integer, ForeignKey("role_definitions.id"), nullable=False, index=True)
            resource_type = Column(String(64), nullable=False)
            action = Column(String(32), nullable=False)
            scope = Column(String(32), default=PermissionScope.GLOBAL.value)
            effect = Column(String(16), default=PermissionEffect.ALLOW.value)
            conditions = Column(JSON, default=dict)
            resource_id = Column(String(128), nullable=True)
            created_at = Column(DateTime, default=datetime.utcnow)

            role = relationship("RoleDefinition", backref="permissions")


        class UserRoleAssignment(Base):
            __tablename__ = "user_role_assignments"

            id = Column(Integer, primary_key=True, autoincrement=True)
            user_id = Column(Integer, nullable=False, index=True)
            role_id = Column(Integer, ForeignKey("role_definitions.id"), nullable=False)
            scope_type = Column(String(32), default=PermissionScope.GLOBAL.value)
            scope_id = Column(String(128), nullable=True)
            granted_by = Column(Integer, nullable=True)
            expires_at = Column(DateTime, nullable=True)
            created_at = Column(DateTime, default=datetime.utcnow)

            role = relationship("RoleDefinition", backref="assignments")


        class PolicyRule(Base):
            __tablename__ = "policy_rules"

            id = Column(Integer, primary_key=True, autoincrement=True)
            name = Column(String(128), unique=True, nullable=False)
            description = Column(String(512), default="")
            resource_type = Column(String(64), nullable=False)
            action = Column(String(32), nullable=False)
            effect = Column(String(16), default=PermissionEffect.ALLOW.value)
            condition_expression = Column(Text, default="")
            priority = Column(Integer, default=0)
            is_active = Column(Boolean, default=True)
            created_at = Column(DateTime, default=datetime.utcnow)
            updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


        class AccessAuditLog(Base):
            __tablename__ = "access_audit_logs"

            id = Column(Integer, primary_key=True, autoincrement=True)
            user_id = Column(Integer, nullable=False, index=True)
            action = Column(String(32), nullable=False)
            resource_type = Column(String(64), nullable=False)
            resource_id = Column(String(128), default="")
            effect = Column(String(16), nullable=False)
            reason = Column(String(512), default="")
            ip_address = Column(String(64), default="")
            request_context = Column(JSON, default=dict)
            created_at = Column(DateTime, default=datetime.utcnow)


        # --- Pydantic schemas ---

        class PermissionCreate(BaseModel):
            resource_type: ResourceType
            action: Action
            scope: PermissionScope = PermissionScope.GLOBAL
            effect: PermissionEffect = PermissionEffect.ALLOW
            conditions: dict[str, Any] = Field(default_factory=dict)
            resource_id: str | None = None


        class PermissionResponse(BaseModel):
            id: int
            role_id: int
            resource_type: str
            action: str
            scope: str
            effect: str
            conditions: dict[str, Any]
            resource_id: str | None
            created_at: datetime

            class Config:
                from_attributes = True


        class RoleDefinitionCreate(BaseModel):
            name: str = Field(..., min_length=1, max_length=64)
            description: str = ""
            is_system: bool = False
            priority: int = 0


        class RoleDefinitionResponse(BaseModel):
            id: int
            name: str
            description: str
            is_system: bool
            priority: int
            permissions: list[PermissionResponse] = []
            created_at: datetime

            class Config:
                from_attributes = True


        class UserRoleAssignmentCreate(BaseModel):
            user_id: int
            role_id: int
            scope_type: PermissionScope = PermissionScope.GLOBAL
            scope_id: str | None = None
            expires_at: datetime | None = None


        class UserRoleAssignmentResponse(BaseModel):
            id: int
            user_id: int
            role_id: int
            scope_type: str
            scope_id: str | None
            granted_by: int | None
            expires_at: datetime | None
            created_at: datetime

            class Config:
                from_attributes = True


        class AccessCheckRequest(BaseModel):
            user_id: int
            resource_type: ResourceType
            action: Action
            resource_id: str | None = None
            context: dict[str, Any] = Field(default_factory=dict)


        class AccessCheckResponse(BaseModel):
            allowed: bool
            reason: str
            matched_rules: list[str] = []


        class PolicyRuleCreate(BaseModel):
            name: str
            resource_type: ResourceType
            action: Action
            effect: PermissionEffect = PermissionEffect.ALLOW
            condition_expression: str = ""
            priority: int = 0


        class PolicyRuleResponse(BaseModel):
            id: int
            name: str
            resource_type: str
            action: str
            effect: str
            condition_expression: str
            priority: int
            is_active: bool
            created_at: datetime

            class Config:
                from_attributes = True
    ''')

    # --- services/permission_service.py ---
    modules["app/services/permission_service.py"] = textwrap.dedent('''\
        """Permission and access control service."""

        from __future__ import annotations

        from datetime import datetime
        from typing import Any, Optional

        import structlog
        from sqlalchemy import select, delete
                from sqlalchemy.ext.asyncio import AsyncSession

        from app.models.permissions import (
            AccessAuditLog,
            AccessCheckResponse,
            Action,
            Permission,
            PermissionCreate,
            PermissionEffect,
            PermissionScope,
            PolicyRule,
            PolicyRuleCreate,
            ResourceType,
            RoleDefinition,
            RoleDefinitionCreate,
            UserRoleAssignment,
            UserRoleAssignmentCreate,
        )

        logger = structlog.get_logger()


        class PermissionService:
            """Role-based access control service."""

            def __init__(self, session: AsyncSession):
                self.session = session

            async def create_role(self, data: RoleDefinitionCreate) -> RoleDefinition:
                """Create a new role definition."""
                role = RoleDefinition(
                    name=data.name,
                    description=data.description,
                    is_system=data.is_system,
                    priority=data.priority,
                )
                self.session.add(role)
                await self.session.commit()
                return role

            async def get_role(self, role_id: int) -> RoleDefinition | None:
                """Get role by ID."""
                result = await self.session.execute(select(RoleDefinition).where(RoleDefinition.id == role_id))
                return result.scalar_one_or_none()

            async def list_roles(self) -> list[RoleDefinition]:
                """List all role definitions."""
                result = await self.session.execute(select(RoleDefinition).order_by(RoleDefinition.priority.desc()))
                return result.scalars().all()

            async def delete_role(self, role_id: int) -> bool:
                """Delete a role definition."""
                role = await self.get_role(role_id)
                if not role or role.is_system:
                    return False
                await self.session.delete(role)
                await self.session.commit()
                return True

            async def add_permission(self, role_id: int, data: PermissionCreate) -> Permission:
                """Add permission to a role."""
                permission = Permission(
                    role_id=role_id,
                    resource_type=data.resource_type.value,
                    action=data.action.value,
                    scope=data.scope.value,
                    effect=data.effect.value,
                    conditions=data.conditions,
                    resource_id=data.resource_id,
                )
                self.session.add(permission)
                await self.session.commit()
                return permission

            async def remove_permission(self, permission_id: int) -> bool:
                """Remove a permission."""
                result = await self.session.execute(select(Permission).where(Permission.id == permission_id))
                perm = result.scalar_one_or_none()
                if perm:
                    await self.session.delete(perm)
                    await self.session.commit()
                    return True
                return False

            async def assign_role(self, data: UserRoleAssignmentCreate, granted_by: int | None = None) -> UserRoleAssignment:
                """Assign role to user."""
                assignment = UserRoleAssignment(
                    user_id=data.user_id,
                    role_id=data.role_id,
                    scope_type=data.scope_type.value,
                    scope_id=data.scope_id,
                    granted_by=granted_by,
                    expires_at=data.expires_at,
                )
                self.session.add(assignment)
                await self.session.commit()
                return assignment

            async def revoke_role(self, assignment_id: int) -> bool:
                """Revoke role assignment."""
                result = await self.session.execute(
                    select(UserRoleAssignment).where(UserRoleAssignment.id == assignment_id)
                )
                assignment = result.scalar_one_or_none()
                if assignment:
                    await self.session.delete(assignment)
                    await self.session.commit()
                    return True
                return False

            async def check_access(
                self,
                user_id: int,
                resource_type: ResourceType,
                action: Action,
                resource_id: str | None = None,
                context: dict[str, Any] | None = None,
            ) -> AccessCheckResponse:
                """Check if user has access to perform action on resource."""
                context = context or {}

                # Get user's active role assignments
                result = await self.session.execute(
                    select(UserRoleAssignment).where(
                        (UserRoleAssignment.user_id == user_id)
                        & ((UserRoleAssignment.expires_at == None) | (UserRoleAssignment.expires_at > datetime.utcnow()))
                    )
                )
                assignments = result.scalars().all()

                if not assignments:
                    return AccessCheckResponse(allowed=False, reason="No role assignments found")

                # Check each role's permissions
                role_ids = [a.role_id for a in assignments]
                perm_result = await self.session.execute(
                    select(Permission).where(
                        (Permission.role_id.in_(role_ids))
                        & (Permission.resource_type == resource_type.value)
                        & (Permission.action == action.value)
                    )
                )
                permissions = perm_result.scalars().all()

                deny_rules: list[str] = []
                allow_rules: list[str] = []

                for perm in permissions:
                    if perm.effect == PermissionEffect.DENY.value:
                        deny_rules.append(f"deny:{perm.resource_type}:{perm.action}")
                    else:
                        allow_rules.append(f"allow:{perm.resource_type}:{perm.action}")

                # Deny takes precedence
                if deny_rules:
                    return AccessCheckResponse(allowed=False, reason="Explicit deny rule matched", matched_rules=deny_rules)

                if allow_rules:
                    return AccessCheckResponse(allowed=True, reason="Allow rule matched", matched_rules=allow_rules)

                return AccessCheckResponse(allowed=False, reason="No matching permission found")

            async def create_policy_rule(self, data: PolicyRuleCreate) -> PolicyRule:
                """Create a policy rule."""
                rule = PolicyRule(
                    name=data.name,
                    resource_type=data.resource_type.value,
                    action=data.action.value,
                    effect=data.effect.value,
                    condition_expression=data.condition_expression,
                    priority=data.priority,
                )
                self.session.add(rule)
                await self.session.commit()
                return rule

            async def list_policy_rules(self, active_only: bool = True) -> list[PolicyRule]:
                """List policy rules."""
                query = select(PolicyRule)
                if active_only:
                    query = query.where(PolicyRule.is_active == True)
                query = query.order_by(PolicyRule.priority.desc())
                result = await self.session.execute(query)
                return result.scalars().all()

            async def log_access_check(
                self,
                user_id: int,
                action: str,
                resource_type: str,
                resource_id: str,
                effect: str,
                reason: str,
                ip_address: str = "",
                context: dict[str, Any] | None = None,
            ) -> AccessAuditLog:
                """Log access check for audit trail."""
                log_entry = AccessAuditLog(
                    user_id=user_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    effect=effect,
                    reason=reason,
                    ip_address=ip_address,
                    request_context=context or {},
                )
                self.session.add(log_entry)
                await self.session.commit()
                return log_entry

            async def get_audit_trail(
                self,
                user_id: int | None = None,
                resource_type: str | None = None,
                page: int = 1,
                page_size: int = 50,
            ) -> tuple[list[AccessAuditLog], int]:
                """Get audit trail with filters."""
                from sqlalchemy import func
                query = select(AccessAuditLog)
                count_query = select(func.count()).select_from(AccessAuditLog)

                if user_id:
                    query = query.where(AccessAuditLog.user_id == user_id)
                    count_query = count_query.where(AccessAuditLog.user_id == user_id)
                if resource_type:
                    query = query.where(AccessAuditLog.resource_type == resource_type)
                    count_query = count_query.where(AccessAuditLog.resource_type == resource_type)

                query = query.order_by(AccessAuditLog.created_at.desc())
                query = query.offset((page - 1) * page_size).limit(page_size)

                result = await self.session.execute(query)
                count_result = await self.session.execute(count_query)
                return result.scalars().all(), count_result.scalar()
    ''')

    return modules


# ============================================================
# 3. Generate audit logging module
# ============================================================
def generate_audit_module():
    modules = {}

    # --- models/audit.py ---
    modules["app/models/audit.py"] = textwrap.dedent('''\
        """Audit logging models for compliance and tracking."""

        from __future__ import annotations

        from datetime import datetime
        from enum import Enum
        from typing import Any, Optional

        from pydantic import BaseModel, Field
        from sqlalchemy import JSON, Column, DateTime, Integer, String, Text, Index
        from sqlalchemy.orm import declarative_base

        Base = declarative_base()


        class AuditEventType(str, Enum):
            USER_LOGIN = "user.login"
            USER_LOGOUT = "user.logout"
            USER_CREATED = "user.created"
            USER_UPDATED = "user.updated"
            USER_DELETED = "user.deleted"
            ROLE_ASSIGNED = "role.assigned"
            ROLE_REVOKED = "role.revoked"
            PERMISSION_DENIED = "permission.denied"
            PERMISSION_GRANTED = "permission.granted"
            AGENT_CREATED = "agent.created"
            AGENT_UPDATED = "agent.updated"
            AGENT_DELETED = "agent.deleted"
            SESSION_STARTED = "session.started"
            SESSION_ENDED = "session.ended"
            DOCUMENT_CREATED = "document.created"
            DOCUMENT_ACCESSED = "document.accessed"
            DOCUMENT_DELETED = "document.deleted"
            WORKFLOW_EXECUTED = "workflow.executed"
            TOOL_CALLED = "tool.called"
            CONFIG_CHANGED = "config.changed"
            DATA_EXPORTED = "data.exported"
            DATA_IMPORTED = "data.imported"
            BILLING_EVENT = "billing.event"
            SECURITY_ALERT = "security.alert"
            SYSTEM_ERROR = "system.error"
            API_KEY_CREATED = "api_key.created"
            API_KEY_REVOKED = "api_key.revoked"
            MFA_ENABLED = "mfa.enabled"
            MFA_DISABLED = "mfa.disabled"
            PASSWORD_RESET = "password.reset"
            SETTINGS_CHANGED = "settings.changed"


        class AuditSeverity(str, Enum):
            INFO = "info"
            WARNING = "warning"
            ERROR = "error"
            CRITICAL = "critical"


        class AuditLogEntry(Base):
            __tablename__ = "audit_log_entries"

            id = Column(Integer, primary_key=True, autoincrement=True)
            event_type = Column(String(64), nullable=False, index=True)
            severity = Column(String(16), default=AuditSeverity.INFO.value, nullable=False)
            actor_id = Column(Integer, nullable=True, index=True)
            actor_type = Column(String(32), default="user")
            actor_name = Column(String(128), default="")
            target_type = Column(String(64), default="")
            target_id = Column(String(128), default="")
            description = Column(String(1024), default="")
            details = Column(JSON, default=dict)
            ip_address = Column(String(64), default="")
            user_agent = Column(String(512), default="")
            request_id = Column(String(128), default="", index=True)
            correlation_id = Column(String(128), default="")
            session_id = Column(String(128), default="")
            outcome = Column(String(32), default="success")
            error_message = Column(String(512), default="")
            duration_ms = Column(Integer, nullable=True)
            created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

            __table_args__ = (
                Index("ix_audit_event_time", "event_type", "created_at"),
                Index("ix_audit_actor_time", "actor_id", "created_at"),
            )


        class AuditLogArchive(Base):
            __tablename__ = "audit_log_archives"

            id = Column(Integer, primary_key=True, autoincrement=True)
            archive_date = Column(DateTime, nullable=False, index=True)
            event_count = Column(Integer, nullable=False)
            storage_path = Column(String(512), nullable=False)
            checksum = Column(String(128), default="")
            created_at = Column(DateTime, default=datetime.utcnow)


        class ComplianceReport(Base):
            __tablename__ = "compliance_reports"

            id = Column(Integer, primary_key=True, autoincrement=True)
            name = Column(String(256), nullable=False)
            report_type = Column(String(64), nullable=False)
            period_start = Column(DateTime, nullable=False)
            period_end = Column(DateTime, nullable=False)
            parameters = Column(JSON, default=dict)
            summary = Column(JSON, default=dict)
            status = Column(String(32), default="pending")
            generated_at = Column(DateTime, nullable=True)
            file_path = Column(String(512), default="")
            created_at = Column(DateTime, default=datetime.utcnow)


        # --- Pydantic schemas ---

        class AuditLogEntryCreate(BaseModel):
            event_type: AuditEventType
            severity: AuditSeverity = AuditSeverity.INFO
            actor_id: int | None = None
            actor_type: str = "user"
            actor_name: str = ""
            target_type: str = ""
            target_id: str = ""
            description: str = ""
            details: dict[str, Any] = Field(default_factory=dict)
            ip_address: str = ""
            user_agent: str = ""
            request_id: str = ""
            correlation_id: str = ""
            session_id: str = ""
            outcome: str = "success"
            error_message: str = ""
            duration_ms: int | None = None


        class AuditLogEntryResponse(BaseModel):
            id: int
            event_type: str
            severity: str
            actor_id: int | None
            actor_type: str
            actor_name: str
            target_type: str
            target_id: str
            description: str
            details: dict[str, Any]
            ip_address: str
            request_id: str
            outcome: str
            duration_ms: int | None
            created_at: datetime

            class Config:
                from_attributes = True


        class AuditLogQuery(BaseModel):
            event_type: AuditEventType | None = None
            severity: AuditSeverity | None = None
            actor_id: int | None = None
            target_type: str | None = None
            target_id: str | None = None
            start_date: datetime | None = None
            end_date: datetime | None = None
            search_text: str | None = None
            page: int = Field(1, ge=1)
            page_size: int = Field(50, ge=1, le=200)


        class AuditLogSummary(BaseModel):
            total_events: int
            event_types: dict[str, int]
            severity_counts: dict[str, int]
            top_actors: list[dict[str, Any]]
            period_start: datetime
            period_end: datetime


        class ComplianceReportCreate(BaseModel):
            name: str
            report_type: str
            period_start: datetime
            period_end: datetime
            parameters: dict[str, Any] = Field(default_factory=dict)


        class ComplianceReportResponse(BaseModel):
            id: int
            name: str
            report_type: str
            period_start: datetime
            period_end: datetime
            status: str
            summary: dict[str, Any]
            generated_at: datetime | None
            created_at: datetime

            class Config:
                from_attributes = True
    ''')

    # --- services/audit_service.py ---
    modules["app/services/audit_service.py"] = textwrap.dedent('''\
        """Audit logging service for compliance and security tracking."""

        from __future__ import annotations

        import hashlib
        import json
        from datetime import datetime, timedelta
        from typing import Any, Optional

        import structlog
        from sqlalchemy import select, func, and_, or_
                from sqlalchemy.ext.asyncio import AsyncSession

        from app.models.audit import (
            AuditLogEntry,
            AuditLogEntryCreate,
            AuditLogArchive,
            AuditLogSummary,
            AuditSeverity,
            ComplianceReport,
            ComplianceReportCreate,
        )

        logger = structlog.get_logger()

        DEFAULT_RETENTION_DAYS = 90
        BATCH_SIZE = 1000


        class AuditService:
            """Comprehensive audit logging service."""

            def __init__(self, session: AsyncSession):
                self.session = session

            async def log_event(self, data: AuditLogEntryCreate) -> AuditLogEntry:
                """Log an audit event."""
                entry = AuditLogEntry(
                    event_type=data.event_type.value,
                    severity=data.severity.value,
                    actor_id=data.actor_id,
                    actor_type=data.actor_type,
                    actor_name=data.actor_name,
                    target_type=data.target_type,
                    target_id=data.target_id,
                    description=data.description,
                    details=data.details,
                    ip_address=data.ip_address,
                    user_agent=data.user_agent,
                    request_id=data.request_id,
                    correlation_id=data.correlation_id,
                    session_id=data.session_id,
                    outcome=data.outcome,
                    error_message=data.error_message,
                    duration_ms=data.duration_ms,
                )
                self.session.add(entry)
                await self.session.commit()
                return entry

            async def log_security_event(
                self,
                event_type: str,
                description: str,
                actor_id: int | None = None,
                severity: AuditSeverity = AuditSeverity.WARNING,
                details: dict[str, Any] | None = None,
            ) -> AuditLogEntry:
                """Log a security-related event."""
                return await self.log_event(
                    AuditLogEntryCreate(
                        event_type=event_type,
                        severity=severity,
                        actor_id=actor_id,
                        description=description,
                        details=details or {},
                    )
                )

            async def query_logs(
                self,
                event_type: str | None = None,
                severity: str | None = None,
                actor_id: int | None = None,
                target_type: str | None = None,
                target_id: str | None = None,
                start_date: datetime | None = None,
                end_date: datetime | None = None,
                search_text: str | None = None,
                page: int = 1,
                page_size: int = 50,
            ) -> tuple[list[AuditLogEntry], int]:
                """Query audit logs with filters."""
                query = select(AuditLogEntry)
                count_query = select(func.count()).select_from(AuditLogEntry)

                filters = []
                if event_type:
                    filters.append(AuditLogEntry.event_type == event_type)
                if severity:
                    filters.append(AuditLogEntry.severity == severity)
                if actor_id:
                    filters.append(AuditLogEntry.actor_id == actor_id)
                if target_type:
                    filters.append(AuditLogEntry.target_type == target_type)
                if target_id:
                    filters.append(AuditLogEntry.target_id == target_id)
                if start_date:
                    filters.append(AuditLogEntry.created_at >= start_date)
                if end_date:
                    filters.append(AuditLogEntry.created_at <= end_date)
                if search_text:
                    filters.append(
                        or_(
                            AuditLogEntry.description.ilike(f"%{search_text}%"),
                            AuditLogEntry.actor_name.ilike(f"%{search_text}%"),
                        )
                    )

                if filters:
                    query = query.where(and_(*filters))
                    count_query = count_query.where(and_(*filters))

                query = query.order_by(AuditLogEntry.created_at.desc())
                query = query.offset((page - 1) * page_size).limit(page_size)

                result = await self.session.execute(query)
                count_result = await self.session.execute(count_query)
                return result.scalars().all(), count_result.scalar()

            async def get_summary(
                self, start_date: datetime | None = None, end_date: datetime | None = None
            ) -> AuditLogSummary:
                """Get audit log summary for a period."""
                start_date = start_date or datetime.utcnow() - timedelta(days=30)
                end_date = end_date or datetime.utcnow()

                # Total events
                total_result = await self.session.execute(
                    select(func.count()).select_from(AuditLogEntry).where(
                        and_(AuditLogEntry.created_at >= start_date, AuditLogEntry.created_at <= end_date)
                    )
                )
                total = total_result.scalar()

                # Event type counts
                type_result = await self.session.execute(
                    select(AuditLogEntry.event_type, func.count())
                    .where(and_(AuditLogEntry.created_at >= start_date, AuditLogEntry.created_at <= end_date))
                    .group_by(AuditLogEntry.event_type)
                )
                event_types = {row[0]: row[1] for row in type_result.all()}

                # Severity counts
                severity_result = await self.session.execute(
                    select(AuditLogEntry.severity, func.count())
                    .where(and_(AuditLogEntry.created_at >= start_date, AuditLogEntry.created_at <= end_date))
                    .group_by(AuditLogEntry.severity)
                )
                severity_counts = {row[0]: row[1] for row in severity_result.all()}

                # Top actors
                actor_result = await self.session.execute(
                    select(AuditLogEntry.actor_id, func.count())
                    .where(and_(AuditLogEntry.created_at >= start_date, AuditLogEntry.created_at <= end_date))
                    .group_by(AuditLogEntry.actor_id)
                    .order_by(func.count().desc())
                    .limit(10)
                )
                top_actors = [{"actor_id": row[0], "count": row[1]} for row in actor_result.all()]

                return AuditLogSummary(
                    total_events=total,
                    event_types=event_types,
                    severity_counts=severity_counts,
                    top_actors=top_actors,
                    period_start=start_date,
                    period_end=end_date,
                )

            async def archive_old_logs(self, retention_days: int = DEFAULT_RETENTION_DAYS) -> int:
                """Archive and purge old audit logs."""
                cutoff = datetime.utcnow() - timedelta(days=retention_days)
                count_result = await self.session.execute(
                    select(func.count()).select_from(AuditLogEntry).where(AuditLogEntry.created_at < cutoff)
                )
                count = count_result.scalar()

                archive = AuditLogArchive(
                    archive_date=datetime.utcnow(),
                    event_count=count,
                    storage_path=f"logs/audit/{datetime.utcnow().strftime('%Y%m%d')}.jsonl",
                    checksum="",
                )
                self.session.add(archive)

                await self.session.execute(
                    delete(AuditLogEntry).where(AuditLogEntry.created_at < cutoff)
                )
                await self.session.commit()
                return count

            async def create_compliance_report(self, data: ComplianceReportCreate) -> ComplianceReport:
                """Create a compliance report."""
                report = ComplianceReport(
                    name=data.name,
                    report_type=data.report_type,
                    period_start=data.period_start,
                    period_end=data.period_end,
                    parameters=data.parameters,
                )
                self.session.add(report)
                await self.session.commit()
                return report

            async def generate_compliance_summary(self, report_id: int) -> dict[str, Any]:
                """Generate compliance summary for a report."""
                result = await self.session.execute(
                    select(ComplianceReport).where(ComplianceReport.id == report_id)
                )
                report = result.scalar_one_or_none()
                if not report:
                    return {}

                summary = await self.get_summary(report.period_start, report.period_end)
                return {
                    "report_id": report_id,
                    "report_name": report.name,
                    "period": f"{report.period_start} to {report.period_end}",
                    "total_events": summary.total_events,
                    "event_breakdown": summary.event_types,
                    "severity_breakdown": summary.severity_counts,
                    "top_actors": summary.top_actors,
                }
    ''')

    return modules


# ============================================================
# 4. Generate billing module
# ============================================================
def generate_billing_module():
    modules = {}

    # --- models/billing.py ---
    modules["app/models/billing.py"] = textwrap.dedent('''\
        """Billing and usage tracking models."""

        from __future__ import annotations

        from datetime import datetime
        from enum import Enum
        from typing import Any, Optional

        from pydantic import BaseModel, Field
        from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, Index
        from sqlalchemy.orm import declarative_base, relationship

        Base = declarative_base()


        class BillingPlanType(str, Enum):
            FREE = "free"
            STARTER = "starter"
            PROFESSIONAL = "professional"
            ENTERPRISE = "enterprise"
            PAY_AS_YOU_GO = "pay_as_you_go"


        class BillingCycle(str, Enum):
            MONTHLY = "monthly"
            QUARTERLY = "quarterly"
            ANNUAL = "annual"
            ONE_TIME = "one_time"


        class SubscriptionStatus(str, Enum):
            ACTIVE = "active"
            PAST_DUE = "past_due"
            CANCELED = "canceled"
            EXPIRED = "expired"
            TRIAL = "trial"


        class InvoiceStatus(str, Enum):
            DRAFT = "draft"
            OPEN = "open"
            PAID = "paid"
            VOID = "void"
            UNCOLLECTIBLE = "uncollectible"


        class PaymentMethodType(str, Enum):
            CREDIT_CARD = "credit_card"
            DEBIT_CARD = "debit_card"
            BANK_TRANSFER = "bank_transfer"
            CRYPTO = "crypto"
            INVOICE = "invoice"
            FREE = "free"


        class BillingPlan(Base):
            __tablename__ = "billing_plans"

            id = Column(Integer, primary_key=True, autoincrement=True)
            name = Column(String(128), unique=True, nullable=False)
            plan_type = Column(String(32), nullable=False)
            description = Column(Text, default="")
            monthly_price = Column(Float, default=0.0)
            annual_price = Column(Float, default=0.0)
            currency = Column(String(8), default="USD")
            included_tokens = Column(Integer, default=0)
            included_requests = Column(Integer, default=0)
            included_storage_mb = Column(Integer, default=0)
            included_agents = Column(Integer, default=1)
            included_users = Column(Integer, default=1)
            overage_token_price = Column(Float, default=0.0)
            overage_request_price = Column(Float, default=0.0)
            features = Column(JSON, default=list)
            is_active = Column(Boolean, default=True)
            is_public = Column(Boolean, default=True)
            created_at = Column(DateTime, default=datetime.utcnow)
            updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


        class Subscription(Base):
            __tablename__ = "subscriptions"

            id = Column(Integer, primary_key=True, autoincrement=True)
            user_id = Column(Integer, nullable=False, index=True)
            plan_id = Column(Integer, ForeignKey("billing_plans.id"), nullable=False)
            status = Column(String(32), default=SubscriptionStatus.ACTIVE.value)
            billing_cycle = Column(String(32), default=BillingCycle.MONTHLY.value)
            current_period_start = Column(DateTime, nullable=False)
            current_period_end = Column(DateTime, nullable=False)
            canceled_at = Column(DateTime, nullable=True)
            trial_ends_at = Column(DateTime, nullable=True)
            payment_method = Column(String(32), default=PaymentMethodType.FREE.value)
            auto_renew = Column(Boolean, default=True)
            metadata_json = Column(JSON, default=dict)
            created_at = Column(DateTime, default=datetime.utcnow)
            updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

            plan = relationship("BillingPlan", backref="subscriptions")


        class UsageRecord(Base):
            __tablename__ = "usage_records"

            id = Column(Integer, primary_key=True, autoincrement=True)
            user_id = Column(Integer, nullable=False, index=True)
            subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
            resource_type = Column(String(64), nullable=False)
            quantity = Column(Float, default=0.0)
            unit = Column(String(32), default="tokens")
            cost = Column(Float, default=0.0)
            model = Column(String(64), default="")
            session_id = Column(String(128), default="")
            agent_id = Column(String(128), default="")
            description = Column(String(512), default="")
            recorded_at = Column(DateTime, default=datetime.utcnow, index=True)

            subscription = relationship("Subscription", backref="usage_records")


        class Invoice(Base):
            __tablename__ = "invoices"

            id = Column(Integer, primary_key=True, autoincrement=True)
            user_id = Column(Integer, nullable=False, index=True)
            subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
            status = Column(String(32), default=InvoiceStatus.DRAFT.value)
            subtotal = Column(Float, default=0.0)
            tax_amount = Column(Float, default=0.0)
            total_amount = Column(Float, default=0.0)
            currency = Column(String(8), default="USD")
            line_items = Column(JSON, default=list)
            issued_at = Column(DateTime, nullable=True)
            due_at = Column(DateTime, nullable=True)
            paid_at = Column(DateTime, nullable=True)
            notes = Column(Text, default="")
            created_at = Column(DateTime, default=datetime.utcnow)

            subscription = relationship("Subscription", backref="invoices")


        class PaymentMethod(Base):
            __tablename__ = "payment_methods"

            id = Column(Integer, primary_key=True, autoincrement=True)
            user_id = Column(Integer, nullable=False, index=True)
            method_type = Column(String(32), nullable=False)
            provider = Column(String(64), default="")
            last_four = Column(String(16), default="")
            is_default = Column(Boolean, default=False)
            token = Column(String(256), default="")
            expires_at = Column(DateTime, nullable=True)
            created_at = Column(DateTime, default=datetime.utcnow)


        class CreditBalance(Base):
            __tablename__ = "credit_balances"

            id = Column(Integer, primary_key=True, autoincrement=True)
            user_id = Column(Integer, unique=True, nullable=False, index=True)
            balance = Column(Float, default=0.0)
            total_purchased = Column(Float, default=0.0)
            total_used = Column(Float, default=0.0)
            updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


        class PromoCode(Base):
            __tablename__ = "promo_codes"

            id = Column(Integer, primary_key=True, autoincrement=True)
            code = Column(String(64), unique=True, nullable=False, index=True)
            discount_type = Column(String(32), nullable=False)
            discount_value = Float(default=0.0)
            max_uses = Column(Integer, default=0)
            current_uses = Column(Integer, default=0)
            valid_from = Column(DateTime, nullable=False)
            valid_until = Column(DateTime, nullable=False)
            is_active = Column(Boolean, default=True)
            created_at = Column(DateTime, default=datetime.utcnow)


        # --- Pydantic schemas ---

        class BillingPlanCreate(BaseModel):
            name: str
            plan_type: BillingPlanType
            description: str = ""
            monthly_price: float = 0.0
            annual_price: float = 0.0
            included_tokens: int = 0
            included_requests: int = 0
            included_storage_mb: int = 0
            included_agents: int = 1
            included_users: int = 1
            overage_token_price: float = 0.0
            features: list[str] = Field(default_factory=list)


        class BillingPlanResponse(BaseModel):
            id: int
            name: str
            plan_type: str
            monthly_price: float
            annual_price: float
            included_tokens: int
            included_requests: int
            included_agents: int
            included_users: int
            features: list[str]
            is_active: bool

            class Config:
                from_attributes = True


        class SubscriptionCreate(BaseModel):
            plan_id: int
            billing_cycle: BillingCycle = BillingCycle.MONTHLY
            payment_method: PaymentMethodType = PaymentMethodType.FREE


        class SubscriptionResponse(BaseModel):
            id: int
            user_id: int
            plan: BillingPlanResponse | None
            status: str
            billing_cycle: str
            current_period_start: datetime
            current_period_end: datetime
            auto_renew: bool

            class Config:
                from_attributes = True


        class UsageRecordCreate(BaseModel):
            user_id: int
            resource_type: str
            quantity: float
            unit: str = "tokens"
            cost: float = 0.0
            model: str = ""
            session_id: str = ""
            agent_id: str = ""
            description: str = ""


        class UsageSummary(BaseModel):
            total_tokens: int
            total_requests: int
            total_cost: float
            period_start: datetime
            period_end: datetime
            breakdown: dict[str, float]


        class InvoiceResponse(BaseModel):
            id: int
            status: str
            total_amount: float
            currency: str
            line_items: list[dict[str, Any]]
            issued_at: datetime | None
            due_at: datetime | None
            paid_at: datetime | None

            class Config:
                from_attributes = True
    ''')

    # --- services/billing_service.py ---
    modules["app/services/billing_service.py"] = textwrap.dedent('''\
        """Billing and usage tracking service."""

        from __future__ import annotations

        from datetime import datetime, timedelta
        from typing import Any, Optional

        import structlog
        from sqlalchemy import select, func, and_
                from sqlalchemy.ext.asyncio import AsyncSession

        from app.models.billing import (
            BillingPlan,
            BillingPlanCreate,
            BillingPlanType,
            CreditBalance,
            Invoice,
            InvoiceStatus,
            Subscription,
            SubscriptionCreate,
            SubscriptionStatus,
            UsageRecord,
            UsageRecordCreate,
            UsageSummary,
        )

        logger = structlog.get_logger()


        class BillingService:
            """Billing and subscription management service."""

            def __init__(self, session: AsyncSession):
                self.session = session

            async def create_plan(self, data: BillingPlanCreate) -> BillingPlan:
                """Create a billing plan."""
                plan = BillingPlan(
                    name=data.name,
                    plan_type=data.plan_type.value,
                    description=data.description,
                    monthly_price=data.monthly_price,
                    annual_price=data.annual_price,
                    included_tokens=data.included_tokens,
                    included_requests=data.included_requests,
                    included_storage_mb=data.included_storage_mb,
                    included_agents=data.included_agents,
                    included_users=data.included_users,
                    overage_token_price=data.overage_token_price,
                    features=data.features,
                )
                self.session.add(plan)
                await self.session.commit()
                return plan

            async def get_plan(self, plan_id: int) -> BillingPlan | None:
                """Get billing plan by ID."""
                result = await self.session.execute(select(BillingPlan).where(BillingPlan.id == plan_id))
                return result.scalar_one_or_none()

            async def list_plans(self, active_only: bool = True) -> list[BillingPlan]:
                """List billing plans."""
                query = select(BillingPlan)
                if active_only:
                    query = query.where(BillingPlan.is_active == True)
                query = query.order_by(BillingPlan.monthly_price)
                result = await self.session.execute(query)
                return result.scalars().all()

            async def create_subscription(self, user_id: int, data: SubscriptionCreate) -> Subscription:
                """Create a subscription for a user."""
                now = datetime.utcnow()
                plan = await self.get_plan(data.plan_id)
                if not plan:
                    raise ValueError("Plan not found")

                period_end = now + timedelta(days=30)
                subscription = Subscription(
                    user_id=user_id,
                    plan_id=data.plan_id,
                    status=SubscriptionStatus.ACTIVE.value,
                    billing_cycle=data.billing_cycle.value,
                    current_period_start=now,
                    current_period_end=period_end,
                    payment_method=data.payment_method.value,
                )
                self.session.add(subscription)
                await self.session.commit()
                return subscription

            async def get_subscription(self, subscription_id: int) -> Subscription | None:
                """Get subscription by ID."""
                result = await self.session.execute(
                    select(Subscription).where(Subscription.id == subscription_id)
                )
                return result.scalar_one_or_none()

            async def get_user_subscription(self, user_id: int) -> Subscription | None:
                """Get active subscription for user."""
                result = await self.session.execute(
                    select(Subscription).where(
                        and_(
                            Subscription.user_id == user_id,
                            Subscription.status == SubscriptionStatus.ACTIVE.value,
                        )
                    )
                )
                return result.scalar_one_or_none()

            async def cancel_subscription(self, subscription_id: int) -> bool:
                """Cancel a subscription."""
                sub = await self.get_subscription(subscription_id)
                if not sub:
                    return False
                sub.status = SubscriptionStatus.CANCELED.value
                sub.canceled_at = datetime.utcnow()
                sub.auto_renew = False
                await self.session.commit()
                return True

            async def record_usage(self, data: UsageRecordCreate) -> UsageRecord:
                """Record usage for billing."""
                record = UsageRecord(
                    user_id=data.user_id,
                    resource_type=data.resource_type,
                    quantity=data.quantity,
                    unit=data.unit,
                    cost=data.cost,
                    model=data.model,
                    session_id=data.session_id,
                    agent_id=data.agent_id,
                    description=data.description,
                )
                self.session.add(record)
                await self.session.commit()
                return record

            async def get_usage_summary(
                self, user_id: int, start_date: datetime | None = None, end_date: datetime | None = None
            ) -> UsageSummary:
            """Get usage summary for a user."""
                start_date = start_date or datetime.utcnow() - timedelta(days=30)
                end_date = end_date or datetime.utcnow()

                result = await self.session.execute(
                    select(
                        func.sum(UsageRecord.quantity),
                        func.count(UsageRecord.id),
                        func.sum(UsageRecord.cost),
                    ).where(
                        and_(
                            UsageRecord.user_id == user_id,
                            UsageRecord.recorded_at >= start_date,
                            UsageRecord.recorded_at <= end_date,
                        )
                    )
                )
                row = result.first()
                total_qty = float(row[0] or 0)
                total_req = int(row[1] or 0)
                total_cost = float(row[2] or 0)

                # Breakdown by resource type
                breakdown_result = await self.session.execute(
                    select(UsageRecord.resource_type, func.sum(UsageRecord.cost))
                    .where(
                        and_(
                            UsageRecord.user_id == user_id,
                            UsageRecord.recorded_at >= start_date,
                            UsageRecord.recorded_at <= end_date,
                        )
                    )
                    .group_by(UsageRecord.resource_type)
                )
                breakdown = {row[0]: float(row[1]) for row in breakdown_result.all()}

                return UsageSummary(
                    total_tokens=int(total_qty),
                    total_requests=total_req,
                    total_cost=total_cost,
                    period_start=start_date,
                    period_end=end_date,
                    breakdown=breakdown,
                )

            async def create_invoice(self, user_id: int, subscription_id: int | None = None) -> Invoice:
                """Create invoice for a user."""
                sub = None
                if subscription_id:
                    sub = await self.get_subscription(subscription_id)

                # Calculate usage costs
                now = datetime.utcnow()
                period_start = now - timedelta(days=30)
                usage = await self.get_usage_summary(user_id, period_start, now)

                line_items = [
                    {"description": "Base subscription", "amount": sub.plan.monthly_price if sub else 0},
                    {"description": "Usage overage", "amount": max(0, usage.total_cost - (sub.plan.monthly_price if sub else 0))},
                ]
                subtotal = sum(item["amount"] for item in line_items)
                tax = subtotal * 0.0
                total = subtotal + tax

                invoice = Invoice(
                    user_id=user_id,
                    subscription_id=subscription_id,
                    status=InvoiceStatus.OPEN.value,
                    subtotal=subtotal,
                    tax_amount=tax,
                    total_amount=total,
                    line_items=line_items,
                    issued_at=now,
                    due_at=now + timedelta(days=30),
                )
                self.session.add(invoice)
                await self.session.commit()
                return invoice

            async def get_credit_balance(self, user_id: int) -> CreditBalance:
            """Get or create credit balance for user."""
                result = await self.session.execute(
                    select(CreditBalance).where(CreditBalance.user_id == user_id)
                )
                balance = result.scalar_one_or_none()
                if not balance:
                    balance = CreditBalance(user_id=user_id, balance=0.0)
                    self.session.add(balance)
                    await self.session.commit()
                return balance

            async def add_credits(self, user_id: int, amount: float) -> CreditBalance:
                """Add credits to user balance."""
                balance = await self.get_credit_balance(user_id)
                balance.balance += amount
                balance.total_purchased += amount
                await self.session.commit()
                return balance

            async def deduct_credits(self, user_id: int, amount: float) -> bool:
                """Deduct credits from user balance."""
                balance = await self.get_credit_balance(user_id)
                if balance.balance < amount:
                    return False
                balance.balance -= amount
                balance.total_used += amount
                await self.session.commit()
                return True
    ''')

    return modules


def main() -> None:
    all_modules: dict[str, str] = {}

    generators = [
        ("user_management", generate_user_management),
        ("permissions", generate_permissions_module),
        ("audit", generate_audit_module),
        ("billing", generate_billing_module),
    ]

    for name, gen_fn in generators:
        print(f"Generating {name}...")
        mods = gen_fn()
        all_modules.update(mods)
        print(f"  {name}: {len(mods)} files")

    print(f"\\nWriting {len(all_modules)} files...")
    for path_str, content in all_modules.items():
        write_file(BASE / path_str, content)

    print(f"Done! Generated {len(all_modules)} modules.")


if __name__ == "__main__":
    main()

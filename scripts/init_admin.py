#!/usr/bin/env python3
"""Initialize the first administrator and a matching API key."""

from __future__ import annotations

import asyncio
import getpass
import os
import sys

from sqlalchemy import select

from app.core.auth_manager import hash_password
from app.middleware.auth import get_user_store
from app.models.users import User, UserRole, UserStatus
from app.storage import async_session, init_db


async def ensure_admin(password: str) -> User:
    """Create the administrator or promote the existing admin account."""
    await init_db()
    async with async_session() as session:
        result = await session.execute(select(User).where(User.username == "admin"))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                username="admin",
                email="admin@localhost",
                hashed_password=hash_password(password),
                role=UserRole.ADMIN.value,
                status=UserStatus.ACTIVE.value,
                is_verified=True,
            )
            session.add(user)
        else:
            user.hashed_password = hash_password(password)
            user.role = UserRole.ADMIN.value
            user.status = UserStatus.ACTIVE.value
        await session.commit()
        await session.refresh(user)
        return user


async def init_admin() -> str:
    """Create or update the administrator and issue a one-time API key."""
    password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Administrator password: ")
    if len(password) < 12:
        raise ValueError("Administrator password must contain at least 12 characters")

    user = await ensure_admin(password)
    raw_key, key_id = get_user_store().create_key(
        owner=user.username,
        scopes=["read", "write", "admin"],
        name="Initial administrator key",
    )

    print(f"Administrator initialized: {user.username}")
    print(f"API key ID: {key_id}")
    print(f"API key (shown once): {raw_key}")
    return raw_key


if __name__ == "__main__":
    try:
        asyncio.run(init_admin())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

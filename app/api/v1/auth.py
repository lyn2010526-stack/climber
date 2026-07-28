"""Authentication endpoints - guest mode compatible."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.storage import async_session
from app.storage.database import User

router = APIRouter()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400


@router.post("/register")
async def register(email: str = Query(...), password: str = Query(...)):
    from app.storage import init_db
    await init_db()
    async with async_session() as session:
        existing = await session.execute(__import__("sqlalchemy").select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")

        import hashlib
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        user = User(email=email, password_hash=password_hash)
        session.add(user)
        await session.commit()
        await session.refresh(user)

        token = secrets.token_urlsafe(32)
        return TokenResponse(access_token=token)


@router.post("/login")
async def login(email: str = Query(...), password: str = Query(...)):
    from app.storage import init_db
    await init_db()
    async with async_session() as session:
        import hashlib
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        result = await session.execute(__import__("sqlalchemy").select(User).where(User.email == email, User.password_hash == password_hash))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = secrets.token_urlsafe(32)
        return TokenResponse(access_token=token)

"""User management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.storage import async_session
from app.storage.auth import DEFAULT_USER_ID
from app.storage.database import User

router = APIRouter()


@router.get("/")
@router.get("")
async def list_users() -> dict:
    async with async_session() as db:
        users = (await db.execute(__import__("sqlalchemy").select(User))).scalars().all()
        return {
            "users": [
                {"id": u.id, "email": u.email, "is_active": u.is_active, "created_at": str(u.created_at)}
                for u in users
            ]
        }


@router.post("/switch")
@router.post("switch")
async def switch_user(payload: dict) -> dict:
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=422, detail="user_id required")
    async with async_session() as db:
        user = (await db.execute(__import__("sqlalchemy").select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return {"ok": True, "user_id": user.id, "email": user.email}

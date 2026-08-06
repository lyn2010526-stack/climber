"""Stats and profile API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from sqlalchemy import func, select

from app.storage import async_session

router = APIRouter()


@router.get("/stats")
@router.get("/stats/")
async def get_stats() -> dict[str, Any]:
    from app.storage.database import Agent, ApiKey, Message, Session, UsageLog
    from app.storage.models_platform import Crew, Workflow

    async with async_session() as db:
        async def count(model) -> int:
            return (await db.execute(select(func.count()).select_from(model))).scalar() or 0

        total_tokens = (await db.execute(select(func.coalesce(func.sum(UsageLog.total_tokens), 0)))).scalar() or 0
        return {
            "total_users": 1,
            "total_agents": await count(Agent),
            "total_api_keys": await count(ApiKey),
            "total_sessions": await count(Session),
            "total_messages": await count(Message),
            "total_tokens": int(total_tokens),
            "total_workflows": await count(Workflow),
            "total_crews": await count(Crew),
        }


@router.get("/profile")
@router.get("/profile/")
async def get_profile() -> dict[str, Any]:
    return {"id": "default-user", "display_name": "Local User", "email": "local@localhost", "is_admin": True}

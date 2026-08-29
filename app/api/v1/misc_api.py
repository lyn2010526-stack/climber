"""Stats, profile, skills, scheduler and search endpoints.

Split out of the former monolithic generic API module (pure move refactor).
Routes are registered with and without a trailing slash because the app runs
with redirect_slashes=False.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select

from app.api.v1._shared import DEFAULT_USER, _payload
from app.core.auth import get_current_user
from app.storage import async_session
from app.storage.models_platform import Crew, Skill, Workflow

router = APIRouter(dependencies=[Depends(get_current_user)])
logger = structlog.get_logger()

# ─── Stats ──────────────────────────────────────────────────────────────────

@router.get("/stats")
@router.get("/stats/")
async def get_stats() -> dict[str, Any]:
    from app.storage.database import Agent, ApiKey, Message, Session, UsageLog

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
    return {"id": DEFAULT_USER, "display_name": "Local User", "email": "local@localhost", "is_admin": True}


# ─── Skills ─────────────────────────────────────────────────────────────────

def _skill_dict(s: Skill) -> dict[str, Any]:
    return {
        "id": s.id,
        "name": s.name,
        "description": s.description,
        "category": s.category,
        "prompt_template": s.prompt_template,
        "tools": s.tools or [],
        "is_enabled": s.is_enabled,
        "use_count": s.use_count,
    }


@router.get("/skills")
@router.get("/skills/")
async def list_skills(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    async with async_session() as db:
        rows = (
            await db.execute(
                select(Skill).order_by(Skill.created_at.desc()).offset(offset).limit(limit)
            )
        ).scalars().all()
        return [_skill_dict(s) for s in rows]


@router.post("/skills")
@router.post("/skills/")
async def create_skill(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    if not data.get("name"):
        raise HTTPException(status_code=422, detail="name is required")
    async with async_session() as db:
        skill = Skill(
            user_id=DEFAULT_USER,
            name=data["name"],
            description=data.get("description", ""),
            category=data.get("category", "general"),
            prompt_template=data.get("prompt_template", ""),
            tools=data.get("tools", []),
        )
        db.add(skill)
        await db.commit()
        await db.refresh(skill)
        return _skill_dict(skill)


async def _set_skill_enabled(skill_id: str, enabled: bool) -> dict:
    async with async_session() as db:
        skill = (await db.execute(select(Skill).where(Skill.id == skill_id))).scalar_one_or_none()
        if skill is None:
            raise HTTPException(status_code=404, detail="Skill not found")
        skill.is_enabled = enabled
        await db.commit()
        return {"ok": True, "id": skill_id, "is_enabled": enabled}


@router.post("/skills/{skill_id}/enable")
async def enable_skill(skill_id: str) -> dict:
    return await _set_skill_enabled(skill_id, True)


@router.post("/skills/{skill_id}/disable")
async def disable_skill(skill_id: str) -> dict:
    return await _set_skill_enabled(skill_id, False)


@router.delete("/skills/{skill_id}")
async def delete_skill(skill_id: str) -> dict:
    async with async_session() as db:
        skill = (await db.execute(select(Skill).where(Skill.id == skill_id))).scalar_one_or_none()
        if skill is None:
            raise HTTPException(status_code=404, detail="Skill not found")
        await db.delete(skill)
        await db.commit()
        return {"ok": True, "deleted": skill_id}


# ─── Scheduler ──────────────────────────────────────────────────────────────

_SCHEDULER_MARKET = [
    {"name": "daily-summary", "cron": "0 9 * * *", "description": "Daily summary at 9am"},
    {"name": "hourly-check", "cron": "0 * * * *", "description": "Hourly health check"},
]


@router.get("/scheduler")
@router.get("/scheduler/")
async def list_scheduled(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    async with async_session() as db:
        rows = (
            await db.execute(
                select(Workflow)
                .where(Workflow.schedule is not None)
                .offset(offset)
                .limit(limit)
            )
        ).scalars().all()
        return [
            {
                "id": w.id,
                "name": w.name,
                "schedule": w.schedule,
                "last_status": w.last_status,
                "run_count": w.run_count,
            }
            for w in rows
        ]


@router.post("/scheduler")
@router.post("/scheduler/")
async def create_scheduled(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    async with async_session() as db:
        wf = Workflow(
            user_id=DEFAULT_USER,
            name=data.get("name", "Scheduled Workflow"),
            nodes=data.get("nodes", []),
            edges=data.get("edges", []),
            schedule=data.get("schedule"),
        )
        db.add(wf)
        await db.commit()
        await db.refresh(wf)
        return {"id": wf.id, "name": wf.name, "schedule": wf.schedule}


# ─── Search ─────────────────────────────────────────────────────────────────

from app.storage.models_platform import DocumentChunk


@router.get("/search")
@router.get("/search/")
async def search_documents(
    q: str = "",
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    if not q:
        return []
    async with async_session() as db:
        pattern = f"%{q}%"
        rows = (
            await db.execute(
                select(DocumentChunk)
                .where(DocumentChunk.content.ilike(pattern))
                .order_by(DocumentChunk.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        ).scalars().all()
        return [
            {
                "id": c.id,
                "document_id": c.document_id,
                "content": c.content,
                "chunk_index": c.chunk_index,
                "score": 0.0,
                "created_at": c.created_at.isoformat() if c.created_at else "",
            }
            for c in rows
        ]

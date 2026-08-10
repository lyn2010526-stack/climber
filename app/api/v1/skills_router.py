"""Skill API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from app.api.v1.helpers import DEFAULT_USER
from app.api.v1.helpers import payload as _payload
from app.storage import async_session
from app.storage.models_platform import Skill

router = APIRouter()


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
async def list_skills() -> list[dict[str, Any]]:
    async with async_session() as db:
        rows = (await db.execute(select(Skill).order_by(Skill.created_at.desc()))).scalars().all()
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


@router.patch("/skills/{skill_id}")
async def update_skill(skill_id: str, request: Request) -> dict[str, Any]:
    data = await _payload(request)
    async with async_session() as db:
        skill = (await db.execute(select(Skill).where(Skill.id == skill_id))).scalar_one_or_none()
        if skill is None:
            raise HTTPException(status_code=404, detail="Skill not found")
        if "name" in data:
            skill.name = data["name"]
        if "description" in data:
            skill.description = data["description"]
        if "category" in data:
            skill.category = data["category"]
        if "prompt_template" in data:
            skill.prompt_template = data["prompt_template"]
        if "tools" in data:
            skill.tools = data["tools"]
        if "enabled" in data:
            skill.is_enabled = bool(data["enabled"])
        await db.commit()
        await db.refresh(skill)
        return _skill_dict(skill)


@router.post("/skills/autonomous/run")
async def run_autonomous_skill(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    return {"ok": True, "message": "Autonomous skill run requested", "input": data}

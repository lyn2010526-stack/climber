"""Skill CRUD API endpoints."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.core.principal import CurrentPrincipal, Principal
from app.schemas.api_v1.base import EmptyRequest
from app.schemas.api_v1.skills import SkillCreateRequest
from app.storage import async_session
from app.storage.models_platform import Skill

logger = structlog.get_logger(__name__)

router = APIRouter()


async def _owned_skill(db: Any, skill_id: str, user_id: str) -> Skill | None:
    """Fetch a skill owned by the given user, or None."""
    return (
        await db.execute(select(Skill).where(Skill.id == skill_id, Skill.user_id == user_id))
    ).scalar_one_or_none()


@router.get("/skills")
@router.get("/skills/", include_in_schema=False)
async def list_skills(principal: CurrentPrincipal) -> list[dict[str, Any]]:
    """List the current user's skills ordered by creation date (newest first)."""
    user_id = principal.subject_id
    async with async_session() as db:
        rows = (
            await db.execute(
                select(Skill).where(Skill.user_id == user_id).order_by(Skill.created_at.desc())
            )
        ).scalars().all()
        return [_skill_dict(s) for s in rows]


@router.post("/skills")
@router.post("/skills/", include_in_schema=False)
async def create_skill(payload: SkillCreateRequest, principal: CurrentPrincipal) -> dict[str, Any]:
    """Create a new skill."""
    data = payload.model_dump()
    user_id = principal.subject_id
    async with async_session() as db:
        skill = Skill(
            user_id=user_id,
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


@router.post("/skills/{skill_id}/enable")
async def enable_skill(
    skill_id: str, principal: CurrentPrincipal, payload: EmptyRequest | None = None
) -> dict[str, Any]:
    """Enable a skill by ID."""
    del payload
    return await _set_skill_enabled(skill_id, True, principal)


@router.post("/skills/{skill_id}/disable")
async def disable_skill(
    skill_id: str, principal: CurrentPrincipal, payload: EmptyRequest | None = None
) -> dict[str, Any]:
    """Disable a skill by ID."""
    del payload
    return await _set_skill_enabled(skill_id, False, principal)


@router.delete("/skills/{skill_id}")
async def delete_skill(skill_id: str, principal: CurrentPrincipal) -> dict[str, bool | str]:
    """Delete a skill by ID."""
    user_id = principal.subject_id
    async with async_session() as db:
        skill = await _owned_skill(db, skill_id, user_id)
        if skill is None:
            raise HTTPException(status_code=404, detail="Skill not found")
        await db.delete(skill)
        await db.commit()
        return {"ok": True, "deleted": skill_id}


async def _set_skill_enabled(
    skill_id: str, enabled: bool, principal: Principal
) -> dict[str, Any]:
    """Set a skill's enabled status.

    Args:
        skill_id: The skill ID to update.
        enabled: True to enable, False to disable.
        request: The HTTP request used to resolve the current user.

    Returns:
        A dictionary with the updated status.
    """
    user_id = principal.subject_id
    async with async_session() as db:
        skill = await _owned_skill(db, skill_id, user_id)
        if skill is None:
            raise HTTPException(status_code=404, detail="Skill not found")
        skill.is_enabled = enabled
        await db.commit()
        return {"ok": True, "id": skill_id, "is_enabled": enabled}


def _skill_dict(s: Skill) -> dict[str, Any]:
    """Convert a Skill model instance to a response dictionary.

    Args:
        s: The Skill database model instance.

    Returns:
        A dictionary with skill fields for API response.
    """
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

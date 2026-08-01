"""Agent API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy import func as sa_func

from app.api.v1.helpers import DEFAULT_USER, payload as _payload
from app.storage import async_session
from app.core.di import resolve as di_resolve

router = APIRouter()


@router.get("/agents")
@router.get("/agents/")
async def list_agents(
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    from app.storage.database import Agent

    async with async_session() as db:
        count_result = await db.execute(
            select(sa_func.count(Agent.id)).where(Agent.user_id == DEFAULT_USER)
        )
        total = count_result.scalar() or 0
        rows = (await db.execute(
            select(Agent).where(Agent.user_id == DEFAULT_USER).order_by(Agent.created_at.desc()).limit(limit).offset(offset)
        )).scalars().all()
        return {
            "items": [
                {
                    "id": a.id,
                    "name": a.name,
                    "description": getattr(a, "description", "") or "",
                    "provider": a.provider,
                    "model_id": a.model_id,
                    "system_prompt": getattr(a, "system_prompt", "") or "",
                    "base_url": a.base_url,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in rows
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }


@router.post("/agents")
@router.post("/agents/")
async def create_agent(request: Request) -> dict[str, Any]:
    from app.storage.database import Agent

    data = await _payload(request)
    if not data.get("name"):
        raise HTTPException(status_code=422, detail="name is required")

    async with async_session() as db:
        agent = Agent(
            user_id=DEFAULT_USER,
            name=data["name"],
            provider=data.get("provider", "openai"),
            model_id=data.get("model_id", "gpt-4o-mini"),
            base_url=data.get("base_url"),
        )
        for field in ("description", "system_prompt", "api_key_encrypted", "tool_ids", "skill_ids"):
            if hasattr(agent, field) and data.get(field) is not None:
                setattr(agent, field, data[field])
        if not getattr(agent, "tool_ids", None):
            tool_registry = di_resolve("ToolRegistry")
            agent.tool_ids = [t.name for t in tool_registry.list_tools()]
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        return {
            "id": agent.id,
            "name": agent.name,
            "provider": agent.provider,
            "model_id": agent.model_id,
            "base_url": agent.base_url,
        }


@router.delete("/agents/{agent_id}")
async def delete_agent(
    agent_id: str,
) -> dict:
    from app.storage.database import Agent

    async with async_session() as db:
        agent = (await db.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        await db.delete(agent)
        await db.commit()
        return {"ok": True, "deleted": agent_id}
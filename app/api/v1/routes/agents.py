"""Agent CRUD API endpoints backed by real database persistence."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.v1.common import ok_response
from app.core.api_key_crypto import encrypt_api_key
from app.core.di import resolve as di_resolve
from app.core.principal import CurrentPrincipal
from app.schemas.api_v1.agents import AgentCreateRequest, AgentResponse
from app.storage import async_session
from app.storage.database import Agent

logger = structlog.get_logger(__name__)

router = APIRouter()


def _owner_filter(principal) -> bool:
    """Local-only mode shows all data; authenticated mode filters by owner."""
    return principal.auth_method != "local"


@router.get("/agents")
@router.get("/agents/", include_in_schema=False)
async def list_agents(principal: CurrentPrincipal) -> list[dict[str, Any]]:
    """List all agents ordered by creation date (newest first)."""
    user_id = principal.subject_id
    async with async_session() as db:
        stmt = select(Agent)
        if _owner_filter(principal):
            stmt = stmt.where(Agent.user_id == user_id)
        rows = (await db.execute(stmt.order_by(Agent.created_at.desc()))).scalars().all()
        return [_agent_dict(a) for a in rows]


@router.post("/agents", response_model=AgentResponse)
@router.post("/agents/", response_model=AgentResponse, include_in_schema=False)
async def create_agent(payload: AgentCreateRequest, principal: CurrentPrincipal) -> dict[str, Any]:
    """Create a new agent with the provided configuration."""
    data = payload.model_dump()
    user_id = principal.subject_id
    async with async_session() as db:
        agent = Agent(
            user_id=user_id,
            name=data["name"],
            provider=data.get("provider", "openai"),
            model_id=data.get("model_id", "gpt-4o-mini"),
            base_url=data.get("base_url"),
            api_key_encrypted=encrypt_api_key(data.get("api_key") or data.get("api_key_encrypted") or "") or None,
        )
        for field in ("description", "system_prompt", "tool_ids", "skill_ids"):
            if hasattr(agent, field) and data.get(field) is not None:
                setattr(agent, field, data[field])
        if not getattr(agent, "tool_ids", None):
            try:
                tool_registry = di_resolve("ToolRegistry")
                agent.tool_ids = [tool.name for tool in tool_registry.list_tools()]
            except KeyError:
                agent.tool_ids = []
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


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str, principal: CurrentPrincipal) -> dict[str, Any]:
    """Get a single agent by ID."""
    user_id = principal.subject_id
    async with async_session() as db:
        stmt = select(Agent).where(Agent.id == agent_id)
        if _owner_filter(principal):
            stmt = stmt.where(Agent.user_id == user_id)
        agent = (await db.execute(stmt)).scalar_one_or_none()
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return _agent_dict(agent)


@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str, principal: CurrentPrincipal) -> dict[str, bool | str]:
    """Delete an agent by ID."""
    user_id = principal.subject_id
    async with async_session() as db:
        stmt = select(Agent).where(Agent.id == agent_id)
        if _owner_filter(principal):
            stmt = stmt.where(Agent.user_id == user_id)
        agent = (await db.execute(stmt)).scalar_one_or_none()
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        await db.delete(agent)
        await db.commit()
        return ok_response(agent_id)


def _agent_dict(a: Agent) -> dict[str, Any]:
    """Convert an Agent model instance to a response dictionary.

    Args:
        a: The Agent database model instance.

    Returns:
        A dictionary with agent fields for API response.
    """
    return {
        "id": a.id,
        "name": a.name,
        "description": getattr(a, "description", "") or "",
        "provider": a.provider,
        "model_id": a.model_id,
        "system_prompt": getattr(a, "system_prompt", "") or "",
        "base_url": a.base_url,
        "tool_ids": getattr(a, "tool_ids", []) or [],
        "skill_ids": getattr(a, "skill_ids", []) or [],
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }

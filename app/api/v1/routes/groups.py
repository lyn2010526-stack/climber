"""Group and group member CRUD API endpoints."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.api_key_crypto import encrypt_api_key
from app.core.principal import CurrentPrincipal
from app.schemas.api_v1.groups import (
    GroupCreateRequest,
    GroupMemberCreateRequest,
    GroupMemberUpdateRequest,
)
from app.storage import async_session
from app.storage.database import Agent
from app.storage.models_groups import AgentGroup, AgentGroupMember, AgentGroupMessage

logger = structlog.get_logger(__name__)

router = APIRouter()


async def _get_owned_group(db: Any, group_id: str, user_id: str, *, with_members: bool = False) -> AgentGroup | None:
    """Fetch a group owned by the given user, or None when not found/owned."""
    stmt = select(AgentGroup).where(AgentGroup.id == group_id, AgentGroup.user_id == user_id)
    if with_members:
        stmt = stmt.options(selectinload(AgentGroup.members))
    return (await db.execute(stmt)).scalars().first()


@router.get("/groups")
@router.get("/groups/", include_in_schema=False)
async def list_groups(principal: CurrentPrincipal) -> list[dict[str, Any]]:
    """List the current user's groups with their members."""
    user_id = principal.subject_id
    async with async_session() as db:
        rows = (
            await db.execute(
                select(AgentGroup)
                .where(AgentGroup.user_id == user_id)
                .options(selectinload(AgentGroup.members))
                .order_by(AgentGroup.created_at.desc())
            )
        ).scalars().all()
        return [_group_dict(g, members=_build_member_dicts(g.members)) for g in rows]


@router.post("/groups")
@router.post("/groups/", include_in_schema=False)
async def create_group(payload: GroupCreateRequest, principal: CurrentPrincipal) -> dict[str, Any]:
    """Create a new group, optionally with default template members."""
    data = payload.model_dump()
    user_id = principal.subject_id
    async with async_session() as db:
        group = AgentGroup(
            user_id=user_id,
            name=data.get("name", "New Group"),
            description=data.get("description", ""),
            topic=data.get("topic", ""),
            status=data.get("status", "active"),
            max_rounds=int(data.get("max_rounds") or 10),
            process_type=data.get("process_type", "sequential"),
        )
        logger.debug("group.process_type", process_type=group.process_type)
        db.add(group)
        await db.commit()
        await db.refresh(group)

        if data.get("template") == "default":
            await _add_default_members(db, group.id, user_id)

        group = (
            await db.execute(
                select(AgentGroup)
                .where(AgentGroup.id == group.id)
                .options(selectinload(AgentGroup.members))
            )
        ).scalars().first()
        return _group_dict(group, members=_build_member_dicts(group.members if group else []))


async def _add_default_members(db: Any, group_id: str, user_id: str) -> None:
    """Add default template members to a group.

    Args:
        db: The async database session.
        group_id: The group ID to add members to.
    """
    agents = (
        await db.execute(
            select(Agent)
            .where(Agent.user_id == user_id)
            .order_by(Agent.created_at.desc())
            .limit(3)
        )
    ).scalars().all()
    roles = ("planner", "executor", "reviewer")
    for agent, role in zip(agents, roles, strict=False):
        member = AgentGroupMember(
            group_id=group_id,
            agent_id=agent.id,
            role=role,
            model_provider=agent.provider,
            model_id=agent.model_id,
        )
        db.add(member)
    await db.commit()


@router.get("/groups/{group_id}")
async def get_group(group_id: str, principal: CurrentPrincipal) -> dict[str, Any]:
    """Get a single group with its members."""
    user_id = principal.subject_id
    async with async_session() as db:
        group = await _get_owned_group(db, group_id, user_id, with_members=True)
        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")
        return _group_dict(group, members=_build_member_dicts(group.members))


@router.delete("/groups/{group_id}")
async def delete_group(group_id: str, principal: CurrentPrincipal) -> dict[str, bool]:
    """Delete a group by ID."""
    user_id = principal.subject_id
    async with async_session() as db:
        group = await _get_owned_group(db, group_id, user_id)
        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")
        await db.delete(group)
        await db.commit()
        return {"ok": True}


@router.post("/groups/{group_id}/members")
async def add_group_member(
    group_id: str, payload: GroupMemberCreateRequest, principal: CurrentPrincipal
) -> dict[str, Any]:
    """Add a member to a group."""
    data = payload.model_dump()
    user_id = principal.subject_id
    async with async_session() as db:
        group = await _get_owned_group(db, group_id, user_id)
        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")
        agent = (
            await db.execute(
                select(Agent).where(Agent.id == payload.agent_id, Agent.user_id == user_id)
            )
        ).scalar_one_or_none()
        if agent is None:
            raise HTTPException(status_code=422, detail="agent_id must reference an owned agent")
        member = AgentGroupMember(
            group_id=group_id,
            agent_id=data.get("agent_id", ""),
            role=data.get("role", "participant"),
            model_provider=data.get("model_provider"),
            model_id=data.get("model_id"),
            api_key_encrypted=encrypt_api_key(
                data.get("api_key") or data.get("api_key_encrypted") or ""
            )
            or None,
            tools=data.get("tools", []),
            is_worker=bool(data.get("is_worker", False)),
        )
        db.add(member)
        await db.commit()
        await db.refresh(member)
        return _member_dict(member)


@router.get("/groups/{group_id}/messages")
async def list_group_messages(
    group_id: str, principal: CurrentPrincipal, limit: int = 50
) -> dict[str, Any]:
    """List messages for a group ordered by creation date (newest first)."""
    user_id = principal.subject_id
    async with async_session() as db:
        group = await _get_owned_group(db, group_id, user_id)
        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")
        rows = (
            await db.execute(
                select(AgentGroupMessage)
                .where(AgentGroupMessage.group_id == group_id)
                .order_by(AgentGroupMessage.created_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        return {"messages": [_message_dict(m) for m in rows]}


@router.delete("/groups/{group_id}/members/{member_id}")
async def remove_group_member(
    group_id: str, member_id: str, principal: CurrentPrincipal
) -> dict[str, bool | str]:
    """Remove a member from a group."""
    user_id = principal.subject_id
    async with async_session() as db:
        group = await _get_owned_group(db, group_id, user_id)
        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")
        member = (
            await db.execute(
                select(AgentGroupMember).where(
                    AgentGroupMember.id == member_id,
                    AgentGroupMember.group_id == group_id,
                )
            )
        ).scalar_one_or_none()
        if member is None:
            raise HTTPException(status_code=404, detail="Member not found")
        await db.delete(member)
        await db.commit()
        return {"ok": True, "deleted": member_id}


@router.patch("/groups/{group_id}/members/{member_id}")
async def update_group_member(
    group_id: str,
    member_id: str,
    payload: GroupMemberUpdateRequest,
    principal: CurrentPrincipal,
) -> dict[str, Any]:
    """Update a group member's fields."""
    data = payload.model_dump(exclude_unset=True)
    user_id = principal.subject_id
    async with async_session() as db:
        group = await _get_owned_group(db, group_id, user_id)
        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")
        member = (
            await db.execute(
                select(AgentGroupMember).where(
                    AgentGroupMember.id == member_id,
                    AgentGroupMember.group_id == group_id,
                )
            )
        ).scalar_one_or_none()
        if member is None:
            raise HTTPException(status_code=404, detail="Member not found")
        if "role" in data:
            member.role = data["role"]
        if "status" in data:
            member.status = data["status"]
        if "is_worker" in data:
            member.is_worker = bool(data["is_worker"])
        if "current_task_id" in data:
            member.current_task_id = data["current_task_id"]
        await db.commit()
        return _member_dict(member)


def _group_dict(
    g: AgentGroup,
    member_count: int = 0,
    members: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Convert an AgentGroup model instance to a response dictionary.

    Args:
        g: The AgentGroup database model instance.
        member_count: The number of members in the group.
        members: Pre-built member dictionaries.

    Returns:
        A dictionary with group fields for API response.
    """
    return {
        "id": g.id,
        "name": g.name,
        "description": g.description,
        "topic": g.topic,
        "status": g.status,
        "max_rounds": g.max_rounds,
        "process_type": getattr(g, "process_type", "sequential"),
        "manager_agent_id": getattr(g, "manager_agent_id", None),
        "manager_llm": getattr(g, "manager_llm", None),
        "member_count": member_count,
        "members": members or [],
        "created_at": g.created_at.isoformat() if g.created_at else "",
    }


def _build_member_dicts(members: list[AgentGroupMember]) -> list[dict[str, Any]]:
    """Build response dictionaries for a list of group members.

    Args:
        members: A list of AgentGroupMember instances.

    Returns:
        A list of member dictionaries.
    """
    return [_member_dict(m) for m in members]


def _member_dict(m: AgentGroupMember) -> dict[str, Any]:
    """Convert an AgentGroupMember model instance to a response dictionary.

    Args:
        m: The AgentGroupMember database model instance.

    Returns:
        A dictionary with member fields for API response.
    """
    return {
        "id": m.id,
        "agent_id": m.agent_id,
        "role": m.role,
        "status": m.status,
        "is_worker": m.is_worker,
        "model_provider": m.model_provider,
        "model_id": m.model_id,
        "tools": m.tools,
        "message_count": m.message_count,
        "last_active": m.last_active.isoformat() if m.last_active else None,
        "current_task_id": getattr(m, "current_task_id", None),
    }


def _message_dict(m: AgentGroupMessage) -> dict[str, Any]:
    """Convert an AgentGroupMessage model instance to a response dictionary.

    Args:
        m: The AgentGroupMessage database model instance.

    Returns:
        A dictionary with message fields for API response.
    """
    return {
        "id": m.id,
        "sender_id": m.sender_id,
        "sender_name": m.sender_name,
        "content": m.content,
        "message_type": m.message_type,
        "created_at": m.created_at.isoformat() if m.created_at else "",
    }

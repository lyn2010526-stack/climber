"""Agent group endpoints.

Split out of the former monolithic generic API module (pure move refactor).
Routes are registered with and without a trailing slash because the app runs
with redirect_slashes=False.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.v1._shared import DEFAULT_USER, _payload
from app.core.api_key_crypto import encrypt_api_key
from app.core.auth import get_current_user
from app.storage import async_session
from app.storage.models_groups import AgentGroup, AgentGroupMember, AgentGroupMessage

router = APIRouter(dependencies=[Depends(get_current_user)])
logger = structlog.get_logger()

# ─── Groups ─────────────────────────────────────────────────────────────────


def _group_dict(g: AgentGroup, member_count: int = 0, members: list[dict[str, Any]] | None = None) -> dict[str, Any]:
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


@router.get("/groups")
@router.get("/groups/")
async def list_groups() -> list[dict[str, Any]]:
    async with async_session() as db:
        rows = (await db.execute(
            select(AgentGroup).options(selectinload(AgentGroup.members)).order_by(AgentGroup.created_at.desc())
        )).scalars().all()
        result = []
        for g in rows:
            members = [
                {
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
                }
                for m in g.members
            ]
            result.append(_group_dict(g, member_count=len(members), members=members))
        return result


@router.post("/groups")
@router.post("/groups/")
async def create_group(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    async with async_session() as db:
        group = AgentGroup(
            user_id=DEFAULT_USER,
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

        # Auto-add default members if template is specified
        template = data.get("template")
        if template == "default":
            default_members = [
                {"agent_id": "planner-1", "role": "planner", "model_provider": "stepfun", "model_id": "step-3.5-flash"},
                {"agent_id": "executor-1", "role": "executor", "model_provider": "stepfun", "model_id": "step-3.5-flash"},
                {"agent_id": "reviewer-1", "role": "reviewer", "model_provider": "stepfun", "model_id": "step-3.5-flash"},
            ]
            for m in default_members:
                member = AgentGroupMember(
                    group_id=group.id,
                    agent_id=m["agent_id"],
                    role=m["role"],
                    model_provider=m["model_provider"],
                    model_id=m["model_id"],
                )
                db.add(member)
            await db.commit()

        # Reload with members for response
        group = (await db.execute(
            select(AgentGroup).where(AgentGroup.id == group.id).options(selectinload(AgentGroup.members))
        )).scalars().first()
        members = [
            {
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
            }
            for m in (group.members if group else [])
        ]
        return _group_dict(group, member_count=len(members), members=members)


@router.get("/groups/{group_id}")
async def get_group(group_id: str) -> dict[str, Any]:
    async with async_session() as db:
        group = (await db.execute(
            select(AgentGroup).where(AgentGroup.id == group_id).options(selectinload(AgentGroup.members))
        )).scalars().first()
        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")
        members = [
            {
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
            }
            for m in group.members
        ]
        return _group_dict(group, member_count=len(members), members=members)


@router.delete("/groups/{group_id}")
async def delete_group(group_id: str) -> dict[str, Any]:
    async with async_session() as db:
        group = (await db.execute(select(AgentGroup).where(AgentGroup.id == group_id))).scalars().first()
        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")
        await db.delete(group)
        await db.commit()
        return {"ok": True}


@router.post("/groups/{group_id}/members")
async def add_group_member(group_id: str, request: Request) -> dict[str, Any]:
    data = await _payload(request)
    async with async_session() as db:
        group = (await db.execute(select(AgentGroup).where(AgentGroup.id == group_id))).scalars().first()
        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")
        member = AgentGroupMember(
            group_id=group_id,
            agent_id=data.get("agent_id", ""),
            role=data.get("role", "participant"),
            model_provider=data.get("model_provider"),
            model_id=data.get("model_id"),
            api_key_encrypted=encrypt_api_key(
                data.get("api_key") or data.get("api_key_encrypted") or ""
            ) or None,
            tools=data.get("tools", []),
            is_worker=bool(data.get("is_worker", False)),
        )
        db.add(member)
        await db.commit()
        await db.refresh(member)
        return {
            "id": member.id,
            "group_id": member.group_id,
            "agent_id": member.agent_id,
            "role": member.role,
            "status": member.status,
            "is_worker": member.is_worker,
        }


@router.get("/groups/{group_id}/messages")
async def list_group_messages(group_id: str, limit: int = 50) -> dict[str, Any]:
    async with async_session() as db:
        rows = (
            await db.execute(
                select(AgentGroupMessage)
                .where(AgentGroupMessage.group_id == group_id)
                .order_by(AgentGroupMessage.created_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        return {
            "messages": [
                {
                    "id": m.id,
                    "sender_id": m.agent_id or "",
                    "agent_id": m.agent_id,
                    "sender_name": m.sender_name,
                    "content": m.content,
                    "message_type": m.message_type,
                    "created_at": m.created_at.isoformat() if m.created_at else "",
                }
                for m in rows
            ]
        }


@router.delete("/groups/{group_id}/members/{member_id}")
async def remove_group_member(group_id: str, member_id: str) -> dict[str, Any]:
    async with async_session() as db:
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
async def update_group_member(group_id: str, member_id: str, request: Request) -> dict[str, Any]:
    data = await _payload(request)
    async with async_session() as db:
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
        return {
            "id": member.id,
            "role": member.role,
            "status": member.status,
            "is_worker": member.is_worker,
            "current_task_id": member.current_task_id,
        }

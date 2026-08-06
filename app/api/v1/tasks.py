"""Task API endpoints."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import exists, or_, select

from app.api.v1.common import current_user_id
from app.api.v1.helpers import payload as _payload
from app.storage import async_session
from app.storage.database import Agent
from app.storage.models_groups import AgentGroup, AgentGroupMember, AgentGroupTask

router = APIRouter()

logger = logging.getLogger(__name__)


def _accessible_group_ids(user_id: str):
    member_exists = exists(
        select(AgentGroupMember.id)
        .join(Agent, Agent.id == AgentGroupMember.agent_id)
        .where(
            AgentGroupMember.group_id == AgentGroup.id,
            Agent.user_id == user_id,
        )
    )
    return select(AgentGroup.id).where(or_(AgentGroup.user_id == user_id, member_exists))


async def _get_accessible_task(db: Any, task_id: str, user_id: str) -> AgentGroupTask:
    task = (
        await db.execute(
            select(AgentGroupTask).where(
                AgentGroupTask.id == task_id,
                AgentGroupTask.group_id.in_(_accessible_group_ids(user_id)),
            )
        )
    ).scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/tasks")
@router.get("/tasks/")
async def list_tasks(request: Request, group_id: str = "") -> list[dict[str, Any]]:
    user_id = current_user_id(request)
    async with async_session() as db:
        stmt = (
            select(AgentGroupTask)
            .where(AgentGroupTask.group_id.in_(_accessible_group_ids(user_id)))
            .order_by(AgentGroupTask.created_at.desc())
        )
        if group_id:
            stmt = stmt.where(AgentGroupTask.group_id == group_id)
        rows = (await db.execute(stmt)).scalars().all()
        return [
            {
                "id": t.id,
                "group_id": t.group_id,
                "description": t.description,
                "status": t.status,
                "worker_id": t.worker_id,
                "current_round": t.current_round,
                "max_rounds": t.max_rounds,
                "total_tokens": t.total_tokens,
                "created_at": t.created_at.isoformat() if t.created_at else "",
            }
            for t in rows
        ]


@router.post("/tasks")
@router.post("/tasks/")
async def create_task(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    user_id = current_user_id(request)
    group_id = data.get("group_id", "")
    async with async_session() as db:
        group = (
            await db.execute(
                select(AgentGroup).where(
                    AgentGroup.id == group_id,
                    AgentGroup.id.in_(_accessible_group_ids(user_id)),
                )
            )
        ).scalar_one_or_none()
        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")
        task = AgentGroupTask(
            group_id=group.id,
            description=data.get("description", ""),
            worker_id=data.get("worker_id") or None,
            reviewer_ids=data.get("reviewer_ids", []),
            max_rounds=int(data.get("max_rounds") or 5),
            context=data.get("context", []),
            guardrails=data.get("guardrails", []),
            human_review_required=bool(data.get("human_review_required", False)),
            output_schema=data.get("output_schema", {}),
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return {
            "id": task.id,
            "group_id": task.group_id,
            "description": task.description,
            "status": task.status,
            "worker_id": task.worker_id,
            "reviewer_ids": task.reviewer_ids,
            "max_rounds": task.max_rounds,
            "context": task.context,
            "guardrails": task.guardrails,
            "human_review_required": task.human_review_required,
            "output_schema": task.output_schema,
        }


@router.post("/tasks/{task_id}/run")
async def run_task(task_id: str, request: Request) -> dict[str, Any]:
    user_id = current_user_id(request)
    async with async_session() as db:
        await _get_accessible_task(db, task_id, user_id)
    try:
        from app.core.group_collaboration import get_group_collaboration_engine

        asyncio.create_task(get_group_collaboration_engine().run_task(task_id))
    except Exception as e:
        logger.error("failed_to_start_task", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start task: {e}") from e
    return {"ok": True, "task_id": task_id, "status": "running"}


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, request: Request) -> dict[str, Any]:
    user_id = current_user_id(request)
    async with async_session() as db:
        task = await _get_accessible_task(db, task_id, user_id)
        return {
            "id": task.id,
            "group_id": task.group_id,
            "description": task.description,
            "status": task.status,
            "worker_id": task.worker_id,
            "reviewer_ids": task.reviewer_ids,
            "current_round": task.current_round,
            "max_rounds": task.max_rounds,
            "context": getattr(task, "context", []),
            "guardrails": getattr(task, "guardrails", []),
            "human_review_required": getattr(task, "human_review_required", False),
            "human_review_status": getattr(task, "human_review_status", "pending"),
            "output_schema": getattr(task, "output_schema", {}),
            "final_output": task.final_output or "",
            "structured_output": getattr(task, "structured_output", {}),
            "total_tokens": task.total_tokens or 0,
            "started_at": task.started_at.isoformat() if task.started_at else "",
            "paused_at": getattr(task, "paused_at", None).isoformat() if getattr(task, "paused_at", None) else "",
            "completed_at": task.completed_at.isoformat() if task.completed_at else "",
            "created_at": task.created_at.isoformat() if task.created_at else "",
            "step_callback": getattr(task, "step_callback", None),
            "task_callback": getattr(task, "task_callback", None),
        }


@router.post("/tasks/{task_id}/pause")
async def pause_task(task_id: str, request: Request) -> dict[str, Any]:
    user_id = current_user_id(request)
    async with async_session() as db:
        task = await _get_accessible_task(db, task_id, user_id)
        if task.status not in ("running",):
            raise HTTPException(status_code=400, detail=f"Cannot pause task in status: {task.status}")
        task.status = "paused"
        task.paused_at = datetime.now(UTC)
        await db.commit()
        return {"ok": True, "task_id": task_id, "status": "paused"}


@router.post("/tasks/{task_id}/resume")
async def resume_task(task_id: str, request: Request) -> dict[str, Any]:
    user_id = current_user_id(request)
    async with async_session() as db:
        task = await _get_accessible_task(db, task_id, user_id)
        if task.status != "paused":
            raise HTTPException(status_code=400, detail=f"Cannot resume task in status: {task.status}")
        task.status = "running"
        task.paused_at = None
        await db.commit()
        return {"ok": True, "task_id": task_id, "status": "running"}


@router.post("/tasks/{task_id}/stop")
async def stop_task(task_id: str, request: Request) -> dict[str, Any]:
    user_id = current_user_id(request)
    async with async_session() as db:
        task = await _get_accessible_task(db, task_id, user_id)
        if task.status in ("completed", "failed", "stopped"):
            raise HTTPException(status_code=400, detail=f"Cannot stop task in status: {task.status}")
        task.status = "stopped"
        task.completed_at = datetime.now(UTC)
        await db.commit()
        return {"ok": True, "task_id": task_id, "status": "stopped"}

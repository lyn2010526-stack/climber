"""Group collaboration task endpoints.

Split out of the former monolithic generic API module (pure move refactor).
Routes are registered with and without a trailing slash because the app runs
with redirect_slashes=False.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from app.api.v1._shared import _payload, _spawn
from app.api.v1.ws import _broadcast_task_update, _task_to_ws_payload
from app.core.auth import get_current_user
from app.storage import async_session
from app.storage.models_groups import AgentGroup, AgentGroupMember, AgentGroupTask

router = APIRouter(dependencies=[Depends(get_current_user)])
logger = structlog.get_logger()

# ─── Tasks ──────────────────────────────────────────────────────────────────

@router.get("/tasks")
@router.get("/tasks/")
async def list_tasks(group_id: str = "") -> list[dict[str, Any]]:
    async with async_session() as db:
        stmt = select(AgentGroupTask).order_by(AgentGroupTask.created_at.desc())
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
    group_id = data.get("group_id") or data.get("groupId") or ""
    async with async_session() as db:
        if not group_id:
            default_group = (
                await db.execute(
                    select(AgentGroup)
                    .where(AgentGroup.name == "Default")
                    .order_by(AgentGroup.created_at.asc())
                )
            ).scalar_one_or_none()
            if default_group is None:
                default_group = AgentGroup(name="Default", description="Auto-created default group")
                db.add(default_group)
                await db.flush()
            group_id = default_group.id
        else:
            group_exists = (
                await db.execute(select(AgentGroup.id).where(AgentGroup.id == group_id))
            ).scalar_one_or_none()
            if group_exists is None:
                raise HTTPException(status_code=404, detail=f"Group '{group_id}' not found")
        worker_id = data.get("worker_id") or None
        if worker_id:
            worker_exists = (
                await db.execute(
                    select(AgentGroupMember.id).where(AgentGroupMember.id == worker_id)
                )
            ).scalar_one_or_none()
            if worker_exists is None:
                worker_id = None
        task = AgentGroupTask(
            group_id=group_id,
            description=data.get("description", ""),
            worker_id=worker_id,
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
            "task_id": task.id,
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
async def run_task(task_id: str) -> dict[str, Any]:
    """Start group collaboration task in background."""
    try:
        from app.core.group_collaboration import group_collaboration_engine
        _spawn(group_collaboration_engine.run_task(task_id))
    except Exception as e:
        logger.error("failed_to_start_task", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start task: {e}") from None
    return {"ok": True, "task_id": task_id, "status": "running"}


@router.get("/tasks/{task_id}")
async def get_task(task_id: str) -> dict[str, Any]:
    async with async_session() as db:
        task = (await db.execute(select(AgentGroupTask).where(AgentGroupTask.id == task_id))).scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
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
            "paused_at": task.paused_at.isoformat() if getattr(task, 'paused_at', None) else "",
            "completed_at": task.completed_at.isoformat() if task.completed_at else "",
            "created_at": task.created_at.isoformat() if task.created_at else "",
            "step_callback": getattr(task, "step_callback", None),
            "task_callback": getattr(task, "task_callback", None),
        }


@router.post("/tasks/{task_id}/pause")
async def pause_task(task_id: str) -> dict[str, Any]:
    async with async_session() as db:
        task = (await db.execute(select(AgentGroupTask).where(AgentGroupTask.id == task_id))).scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if task.status not in ("running",):
            raise HTTPException(status_code=400, detail=f"Cannot pause task in status: {task.status}")
        task.status = "paused"
        task.paused_at = datetime.now(UTC)
        await db.commit()
        await _broadcast_task_update(task.id, await _task_to_ws_payload(task))
        return {"ok": True, "task_id": task_id, "status": "paused"}


@router.post("/tasks/{task_id}/resume")
async def resume_task(task_id: str) -> dict[str, Any]:
    async with async_session() as db:
        task = (await db.execute(select(AgentGroupTask).where(AgentGroupTask.id == task_id))).scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if task.status != "paused":
            raise HTTPException(status_code=400, detail=f"Cannot resume task in status: {task.status}")
        task.status = "running"
        task.paused_at = None
        await db.commit()
        await _broadcast_task_update(task.id, await _task_to_ws_payload(task))
        return {"ok": True, "task_id": task_id, "status": "running"}


@router.post("/tasks/{task_id}/stop")
async def stop_task(task_id: str) -> dict[str, Any]:
    async with async_session() as db:
        task = (await db.execute(select(AgentGroupTask).where(AgentGroupTask.id == task_id))).scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if task.status in ("completed", "failed", "stopped"):
            raise HTTPException(status_code=400, detail=f"Cannot stop task in status: {task.status}")
        task.status = "stopped"
        task.completed_at = datetime.now(UTC)
        await db.commit()
        await _broadcast_task_update(task.id, await _task_to_ws_payload(task))
        return {"ok": True, "task_id": task_id, "status": "stopped"}


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str) -> dict[str, Any]:
    """Cancel a running task, marking it as cancelled (reuses stop semantics)."""
    async with async_session() as db:
        task = (await db.execute(select(AgentGroupTask).where(AgentGroupTask.id == task_id))).scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if task.status in ("completed", "failed", "stopped", "cancelled"):
            raise HTTPException(status_code=400, detail=f"Cannot cancel task in status: {task.status}")
        task.status = "cancelled"
        task.completed_at = datetime.now(UTC)
        await db.commit()
        await _broadcast_task_update(task.id, await _task_to_ws_payload(task))
        return {"ok": True, "task_id": task_id, "status": "cancelled"}

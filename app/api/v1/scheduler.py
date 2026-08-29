"""Scheduler API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select

from app.api.v1.helpers import DEFAULT_USER
from app.api.v1.helpers import payload as _payload
from app.core.auth import get_current_user
from app.storage import async_session
from app.storage.models_platform import Workflow

router = APIRouter(dependencies=[Depends(get_current_user)])

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
        return [{"id": w.id, "name": w.name, "schedule": w.schedule, "last_status": w.last_status, "run_count": w.run_count} for w in rows]


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


# /scheduler/tasks endpoints (frontend compatibility)

@router.get("/scheduler/tasks")
@router.get("/scheduler/tasks/")
async def list_scheduler_tasks(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    async with async_session() as db:
        rows = (
            await db.execute(
                select(Workflow)
                .where(Workflow.schedule is not None)
                .order_by(Workflow.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        ).scalars().all()
        return [{"id": w.id, "name": w.name, "cron": w.schedule, "description": getattr(w, "description", ""), "enabled": True, "last_run": None, "next_run": None, "run_count": w.run_count or 0} for w in rows]


@router.post("/scheduler/tasks")
@router.post("/scheduler/tasks/")
async def create_scheduler_task(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    async with async_session() as db:
        wf = Workflow(
            user_id=DEFAULT_USER,
            name=data.get("name", "Scheduled Task"),
            description=data.get("description", ""),
            nodes=data.get("nodes", []),
            edges=data.get("edges", []),
            schedule=data.get("cron") or data.get("schedule"),
        )
        db.add(wf)
        await db.commit()
        await db.refresh(wf)
        return {"id": wf.id, "name": wf.name, "cron": wf.schedule, "description": wf.description, "enabled": True, "last_run": None, "next_run": None, "run_count": 0}


@router.patch("/scheduler/tasks/{task_id}")
async def update_scheduler_task(task_id: str, request: Request) -> dict[str, Any]:
    data = await _payload(request)
    async with async_session() as db:
        wf = (await db.execute(select(Workflow).where(Workflow.id == task_id))).scalar_one_or_none()
        if wf is None:
            raise HTTPException(status_code=404, detail="Scheduler task not found")
        if "name" in data:
            wf.name = data["name"]
        if "description" in data:
            wf.description = data["description"]
        if "cron" in data or "schedule" in data:
            wf.schedule = data.get("cron", data.get("schedule"))
        if "enabled" in data:
            wf.status = "active" if data["enabled"] else "inactive"
        await db.commit()
        await db.refresh(wf)
        return {"id": wf.id, "name": wf.name, "cron": wf.schedule, "description": wf.description, "enabled": wf.status != "inactive", "last_run": None, "next_run": None, "run_count": wf.run_count or 0}


@router.delete("/scheduler/tasks/{task_id}")
async def delete_scheduler_task(task_id: str) -> dict[str, Any]:
    async with async_session() as db:
        wf = (await db.execute(select(Workflow).where(Workflow.id == task_id))).scalar_one_or_none()
        if wf is None:
            raise HTTPException(status_code=404, detail="Scheduler task not found")
        await db.delete(wf)
        await db.commit()
        return {"ok": True, "deleted": task_id}

"""Scheduler API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from sqlalchemy import select

from app.api.v1.helpers import DEFAULT_USER, payload as _payload
from app.storage import async_session
from app.storage.models_platform import Workflow

router = APIRouter()

_SCHEDULER_MARKET = [
    {"name": "daily-summary", "cron": "0 9 * * *", "description": "Daily summary at 9am"},
    {"name": "hourly-check", "cron": "0 * * * *", "description": "Hourly health check"},
]


@router.get("/scheduler")
@router.get("/scheduler/")
async def list_scheduled() -> list[dict[str, Any]]:
    async with async_session() as db:
        rows = (await db.execute(select(Workflow).where(Workflow.schedule != None))).scalars().all()
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
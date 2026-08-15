"""Task API endpoints."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from app.api.v1.helpers import payload as _payload
from app.storage import async_session
from app.storage.models_groups import AgentGroupTask

router = APIRouter()
logger = logging.getLogger(__name__)

_background_tasks: set[asyncio.Task] = set()


def _spawn(coro: Any) -> None:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


# ─── TTL cache for tasks list (keyed by group_id) ─────────────────────────────

class _TasksCache:
    """Process-scoped TTL cache keyed by query params."""

    def __init__(self, ttl: float) -> None:
        self._ttl = ttl
        self._data: dict[str, tuple[list[dict] | None, float]] = {}

    def get(self, key: str) -> list[dict] | None:
        entry = self._data.get(key)
        if entry is not None:
            data, ts = entry
            if time.monotonic() - ts < self._ttl:
                return data
            del self._data[key]
        return None

    def set(self, key: str, value: list[dict] | None) -> None:
        self._data[key] = (value, time.monotonic())

    def invalidate_all(self) -> None:
        self._data.clear()


_tasks_cache = _TasksCache(ttl=60.0)  # 1 min

# Per-key detail cache for individual tasks
_task_detail_cache: dict[str, tuple[dict, float]] = {}
_TASK_DETAIL_TTL = 30.0


def _get_cached_task(task_id: str) -> dict | None:
    entry = _task_detail_cache.get(task_id)
    if entry is not None:
        data, ts = entry
        if time.monotonic() - ts < _TASK_DETAIL_TTL:
            return data
        del _task_detail_cache[task_id]
    return None


def _set_cached_task(task_id: str, data: dict) -> None:
    _task_detail_cache[task_id] = (data, time.monotonic())


def _invalidate_task(task_id: str) -> None:
    _task_detail_cache.pop(task_id, None)


@router.get("/tasks")
@router.get("/tasks/")
async def list_tasks(group_id: str = "") -> list[dict[str, Any]]:
    cache_key = f"g:{group_id}"
    cached = _tasks_cache.get(cache_key)
    if cached is not None:
        return cached

    async with async_session() as db:
        stmt = select(AgentGroupTask).order_by(AgentGroupTask.created_at.desc())
        if group_id:
            stmt = stmt.where(AgentGroupTask.group_id == group_id)
        rows = (await db.execute(stmt)).scalars().all()
        result = [
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
    _tasks_cache.set(cache_key, result)
    return result


@router.post("/tasks")
@router.post("/tasks/")
async def create_task(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    async with async_session() as db:
        task = AgentGroupTask(
            group_id=data.get("group_id", ""), description=data.get("description", ""),
            worker_id=data.get("worker_id") or None, reviewer_ids=data.get("reviewer_ids", []),
            max_rounds=int(data.get("max_rounds") or 5), context=data.get("context", []),
            guardrails=data.get("guardrails", []), human_review_required=bool(data.get("human_review_required", False)),
            output_schema=data.get("output_schema", {}),
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        _tasks_cache.invalidate_all()  # invalidate
        _invalidate_task(task.id)
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
            "output_schema": task.output_schema
        }


@router.post("/tasks/{task_id}/run")
async def run_task(task_id: str) -> dict[str, Any]:
    try:
        from app.core.group_collaboration import get_group_collaboration_engine
        _spawn(get_group_collaboration_engine().run_task(task_id))
    except Exception as e:
        logger.error("failed_to_start_task", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start task: {e}") from None
    return {"ok": True, "task_id": task_id, "status": "running"}


@router.get("/tasks/{task_id}")
async def get_task(task_id: str) -> dict[str, Any]:
    cached = _get_cached_task(task_id)
    if cached is not None:
        return cached

    async with async_session() as db:
        task = (await db.execute(select(AgentGroupTask).where(AgentGroupTask.id == task_id))).scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        result = {
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
            "paused_at": getattr(task, 'paused_at', None).isoformat() if getattr(task, 'paused_at', None) else "",
            "completed_at": task.completed_at.isoformat() if task.completed_at else "",
            "created_at": task.created_at.isoformat() if task.created_at else "",
            "step_callback": getattr(task, "step_callback", None),
            "task_callback": getattr(task, "task_callback", None),
        }
    _set_cached_task(task_id, result)
    return result


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
        _invalidate_task(task_id)
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
        _invalidate_task(task_id)
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
        _invalidate_task(task_id)
        return {"ok": True, "task_id": task_id, "status": "stopped"}

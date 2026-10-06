"""Scheduler API endpoints.

Dead-code cleanup (2026-10-05): the ``/scheduler`` GET/POST handlers were
never mounted — ``app/api/v1/__init__.py`` only extracts the
``/scheduler/tasks`` prefix from this router — and the live versions exist in
``app/api/v1/routes/misc.py``.  They were removed per
``docs/audits/dead-code-scan.md``.  Only the ``/scheduler/tasks`` CRUD
endpoints below are actually served.
"""

from __future__ import annotations

import contextlib
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from app.api.v1.common import current_user_id
from app.api.v1.helpers import payload as _payload
from app.core.auth_manager import require_scopes
from app.core.di import resolve as di_resolve
from app.storage import async_session
from app.storage.models_platform import Workflow

router = APIRouter()


def _scheduler() -> Any:
    """Return the runtime scheduler (DI singleton, else the module fallback)."""
    try:
        return di_resolve("TaskScheduler")
    except KeyError:
        from app.core.scheduler import task_scheduler

        return task_scheduler


async def _run_scheduled_workflow(task: Any) -> None:
    """Execute the stored workflow behind a scheduled task entry."""
    from app.core.agent_engine import AgentEngine
    from app.core.workflow_executor import build_workflow_from_graph
    from app.workflow.engine import WorkflowEngine

    async with async_session() as db:
        wf = (await db.execute(select(Workflow).where(Workflow.id == task.id))).scalar_one_or_none()
    if wf is None:
        task.config["last_error"] = "Scheduled workflow no longer exists"
        return
    nodes, edges = wf.nodes or [], wf.edges or []
    if not nodes:
        task.config["last_error"] = "Scheduled workflow has no nodes"
        return
    try:
        model_registry: Any = di_resolve("ModelRegistry")
    except KeyError:
        from app.models.registry import ModelRegistry

        model_registry = ModelRegistry()
    try:
        tool_registry: Any = di_resolve("ToolRegistry")
    except KeyError:
        from app.tools import ToolRegistry

        tool_registry = ToolRegistry()
    agent_engine = AgentEngine(model_registry=model_registry, tool_registry=tool_registry)
    workflow = build_workflow_from_graph(nodes, edges, name=wf.name)
    engine = WorkflowEngine(engine=agent_engine, model_registry=model_registry)
    try:
        result = await engine.execute(workflow, user_inputs={"schedule": task.name})
        status = getattr(result, "status", "completed")
    except Exception as exc:
        task.config["last_error"] = str(exc)
        status = "failed"
    async with async_session() as db:
        record = (
            await db.execute(select(Workflow).where(Workflow.id == task.id))
        ).scalar_one_or_none()
        if record is not None:
            record.run_count = (record.run_count or 0) + 1
            record.last_status = status
            await db.commit()
    task.config["last_status"] = status


def _ensure_scheduler_handler() -> None:
    """Register the workflow handler once so scheduled tasks enter the runtime."""
    with contextlib.suppress(Exception):
        _scheduler().register_handler("workflow", _run_scheduled_workflow)


def _register_scheduled_task(wf: Any) -> None:
    """Mirror a persisted scheduled workflow into the runtime scheduler."""
    from app.core.scheduler import ScheduledTask

    _ensure_scheduler_handler()
    with contextlib.suppress(Exception):
        _scheduler().add_task(
            ScheduledTask(
                id=wf.id,
                name=wf.name,
                description=getattr(wf, "description", "") or "",
                cron_expression=wf.schedule or "0 9 * * *",
                task_type="workflow",
                enabled=getattr(wf, "last_status", None) != "inactive",
            )
        )


# /scheduler/tasks endpoints (frontend compatibility)


@router.get("/scheduler/tasks")
@router.get("/scheduler/tasks/")
async def list_scheduler_tasks(request: Request) -> list[dict[str, Any]]:
    async with async_session() as db:
        user_id = current_user_id(request)
        rows = (
            (
                await db.execute(
                    select(Workflow)
                    .where(Workflow.schedule.isnot(None), Workflow.user_id == user_id)
                    .order_by(Workflow.created_at.desc())
                )
            )
            .scalars()
            .all()
        )
        return [
            {
                "id": w.id,
                "name": w.name,
                "cron": w.schedule,
                "description": getattr(w, "description", ""),
                "enabled": getattr(w, "last_status", None) != "inactive",
                "last_run": None,
                "next_run": None,
                "run_count": w.run_count or 0,
            }
            for w in rows
        ]


@router.post("/scheduler/tasks")
@router.post("/scheduler/tasks/")
async def create_scheduler_task(
    request: Request,
    _auth: dict[str, Any] = Depends(require_scopes("write")),
) -> dict[str, Any]:
    data = await _payload(request)
    await _ensure_scheduler_handler()  # type: ignore[misc, func-returns-value]  # helper is sync; await preserved to keep runtime behavior
    async with async_session() as db:
        wf = Workflow(
            user_id=current_user_id(request),
            name=data.get("name", "Scheduled Task"),
            description=data.get("description", ""),
            nodes=data.get("nodes", []),
            edges=data.get("edges", []),
            schedule=data.get("cron") or data.get("schedule"),
        )
        db.add(wf)
        await db.commit()
        await db.refresh(wf)
        _register_scheduled_task(wf)
        return {
            "id": wf.id,
            "name": wf.name,
            "cron": wf.schedule,
            "description": wf.description,
            "enabled": True,
            "last_run": None,
            "next_run": None,
            "run_count": 0,
        }


@router.patch("/scheduler/tasks/{task_id}")
async def update_scheduler_task(
    task_id: str,
    request: Request,
    _auth: dict[str, Any] = Depends(require_scopes("write")),
) -> dict[str, Any]:
    data = await _payload(request)
    async with async_session() as db:
        user_id = current_user_id(request)
        wf = (
            await db.execute(
                select(Workflow).where(Workflow.id == task_id, Workflow.user_id == user_id)
            )
        ).scalar_one_or_none()
        if wf is None:
            raise HTTPException(status_code=404, detail="Scheduler task not found")
        if "name" in data:
            wf.name = data["name"]
        if "description" in data:
            wf.description = data["description"]
        if "cron" in data or "schedule" in data:
            wf.schedule = data.get("cron", data.get("schedule"))
        if "enabled" in data:
            wf.last_status = "active" if data["enabled"] else "inactive"
        await db.commit()
        await db.refresh(wf)
        if wf.schedule:
            _register_scheduled_task(wf)
        return {
            "id": wf.id,
            "name": wf.name,
            "cron": wf.schedule,
            "description": wf.description,
            "enabled": wf.last_status != "inactive",
            "last_run": None,
            "next_run": None,
            "run_count": wf.run_count or 0,
        }


@router.delete("/scheduler/tasks/{task_id}")
async def delete_scheduler_task(
    task_id: str,
    request: Request,
    _auth: dict[str, Any] = Depends(require_scopes("write")),
) -> dict[str, Any]:
    async with async_session() as db:
        user_id = current_user_id(request)
        wf = (
            await db.execute(
                select(Workflow).where(Workflow.id == task_id, Workflow.user_id == user_id)
            )
        ).scalar_one_or_none()
        if wf is None:
            raise HTTPException(status_code=404, detail="Scheduler task not found")
        await db.delete(wf)
        await db.commit()
        _scheduler().remove_task(task_id)
        return {"ok": True, "deleted": task_id}

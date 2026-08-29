"""Crew API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import delete as sa_delete
from sqlalchemy import select

from app.api.v1.helpers import DEFAULT_USER
from app.api.v1.helpers import payload as _payload
from app.core.api_key_crypto import decrypt_api_key
from app.core.auth import get_current_user
from app.core.di import resolve as di_resolve
from app.storage import async_session
from app.storage.models_platform import Crew, CrewRun

router = APIRouter(dependencies=[Depends(get_current_user)])


def _crew_dict(c: Crew) -> dict[str, Any]:
    return {
        "id": c.id,
        "name": c.name,
        "description": c.description,
        "process": c.process,
        "agents": c.agents or [],
        "tasks": c.tasks or [],
        "run_count": c.run_count,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


@router.get("/crews")
@router.get("/crews/")
async def list_crews(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    async with async_session() as db:
        rows = (
            await db.execute(
                select(Crew).order_by(Crew.created_at.desc()).offset(offset).limit(limit)
            )
        ).scalars().all()
        return [_crew_dict(c) for c in rows]


@router.post("/crews")
@router.post("/crews/")
async def create_crew(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    if not data.get("name"):
        raise HTTPException(status_code=422, detail="name is required")
    async with async_session() as db:
        crew = Crew(
            user_id=DEFAULT_USER,
            name=data["name"],
            description=data.get("description", ""),
            process=data.get("process", "sequential"),
            agents=data.get("agents", []),
            tasks=data.get("tasks", []),
        )
        db.add(crew)
        await db.commit()
        await db.refresh(crew)
        return _crew_dict(crew)


@router.delete("/crews/{crew_id}")
async def delete_crew(crew_id: str) -> dict:
    async with async_session() as db:
        crew = (await db.execute(select(Crew).where(Crew.id == crew_id))).scalar_one_or_none()
        if crew is None:
            raise HTTPException(status_code=404, detail="Crew not found")
        await db.execute(sa_delete(CrewRun).where(CrewRun.crew_id == crew_id))
        await db.delete(crew)
        await db.commit()
        return {"ok": True, "deleted": crew_id}


@router.post("/crews/{crew_id}/run")
async def run_crew(crew_id: str, request: Request) -> dict[str, Any]:
    from app.core.agent_engine import AgentEngine
    from app.storage.database import Agent

    data = await _payload(request)

    async with async_session() as db:
        crew = (await db.execute(select(Crew).where(Crew.id == crew_id))).scalar_one_or_none()
        if crew is None:
            raise HTTPException(status_code=404, detail="Crew not found")
        crew_name, crew_tasks = crew.name, list(crew.tasks or [])
        agent_row = (await db.execute(select(Agent).limit(1))).scalar_one_or_none()

    if agent_row is None:
        raise HTTPException(status_code=422, detail="No agent configured; create an agent first")
    if not crew_tasks:
        raise HTTPException(status_code=422, detail="Crew has no tasks defined")

    model_registry = di_resolve("ModelRegistry")
    tool_registry = di_resolve("ToolRegistry")
    engine = AgentEngine(model_registry=model_registry, tool_registry=tool_registry)
    task_results: list[dict[str, Any]] = []
    transcript = ""
    status = "completed"
    error = ""

    try:
        for idx, task in enumerate(crew_tasks):
            description = task.get("description") or task.get("name") or f"Task {idx + 1}"
            prompt = description if not transcript else f"{description}\n\n\u4e0a\u4e00\u6b65\u7ed3\u679c\uff1a\n{transcript}"

            session = engine.create_session(
                agent_id=agent_row.id,
                user_id=DEFAULT_USER,
                provider=agent_row.provider,
                model_id=agent_row.model_id,
                api_key=decrypt_api_key(getattr(agent_row, "api_key_encrypted", "") or ""),
                base_url=agent_row.base_url,
                system_prompt=task.get("system_prompt", f"You are part of crew '{crew_name}'."),
            )
            parts: list[str] = []
            async for event in engine.run(session, prompt):
                if event.type.value == "text":
                    parts.append(event.data.get("content", ""))
                elif event.type.value == "error":
                    raise RuntimeError(event.data.get("error", "agent error"))
            transcript = "".join(parts)
            task_results.append({"task": description, "output": transcript})
    except Exception as e:
        status = "failed"
        error = str(e)

    async with async_session() as db:
        run = CrewRun(
            crew_id=crew_id,
            status=status,
            inputs=data.get("inputs", {}),
            output=transcript,
            task_results=task_results,
            error=error,
        )
        db.add(run)
        stored = (await db.execute(select(Crew).where(Crew.id == crew_id))).scalar_one_or_none()
        if stored is not None:
            stored.run_count = (stored.run_count or 0) + 1
        await db.commit()

    return {
        "id": crew_id,
        "status": status,
        "output": transcript,
        "task_results": task_results,
        "error": error,
    }

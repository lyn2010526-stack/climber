"""Crew CRUD and execution API endpoints."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from sqlalchemy import delete as sa_delete
from sqlalchemy import select

from app.api.v1.common import ok_response, redact_sensitive_fields
from app.core.api_key_crypto import decrypt_api_key
from app.core.di import resolve as di_resolve
from app.core.principal import CurrentPrincipal
from app.schemas.api_v1.crews import CrewCreateRequest, CrewRunRequest
from app.storage import async_session
from app.storage.database import Agent
from app.storage.models_platform import Crew, CrewRun

logger = structlog.get_logger(__name__)

router = APIRouter()


async def _owned_crew(db: Any, crew_id: str, user_id: str) -> Crew | None:
    """Fetch a crew owned by the given user, or None."""
    return (
        await db.execute(select(Crew).where(Crew.id == crew_id, Crew.user_id == user_id))
    ).scalar_one_or_none()


@router.get("/crews")
@router.get("/crews/", include_in_schema=False)
async def list_crews(principal: CurrentPrincipal) -> list[dict[str, Any]]:
    """List the current user's crews ordered by creation date (newest first)."""
    user_id = principal.subject_id
    async with async_session() as db:
        rows = (
            await db.execute(
                select(Crew).where(Crew.user_id == user_id).order_by(Crew.created_at.desc())
            )
        ).scalars().all()
        return [_crew_dict(c) for c in rows]


@router.post("/crews")
@router.post("/crews/", include_in_schema=False)
async def create_crew(payload: CrewCreateRequest, principal: CurrentPrincipal) -> dict[str, Any]:
    """Create a new crew."""
    data = payload.model_dump()
    user_id = principal.subject_id
    async with async_session() as db:
        agent_ids = {
            str(item["agent_id"])
            for item in payload.agents
            if isinstance(item, dict) and item.get("agent_id")
        }
        if agent_ids:
            owned_agent_ids = set(
                (
                    await db.execute(
                        select(Agent.id).where(
                            Agent.user_id == user_id,
                            Agent.id.in_(agent_ids),
                        )
                    )
                ).scalars().all()
            )
            if owned_agent_ids != agent_ids:
                raise HTTPException(
                    status_code=422,
                    detail="Crew agents must reference owned agents",
                )
        crew = Crew(
            user_id=user_id,
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
async def delete_crew(crew_id: str, principal: CurrentPrincipal) -> dict[str, bool | str]:
    """Delete a crew and its run history."""
    user_id = principal.subject_id
    async with async_session() as db:
        crew = await _owned_crew(db, crew_id, user_id)
        if crew is None:
            raise HTTPException(status_code=404, detail="Crew not found")
        await db.execute(sa_delete(CrewRun).where(CrewRun.crew_id == crew_id))
        await db.delete(crew)
        await db.commit()
        return ok_response(crew_id)


@router.post("/crews/{crew_id}/run")
async def run_crew(
    crew_id: str, payload: CrewRunRequest, principal: CurrentPrincipal
) -> dict[str, Any]:
    """Run a crew's tasks sequentially through the agent engine."""
    from app.core.agent_engine import AgentEngine

    data = payload.model_dump()
    user_id = principal.subject_id

    async with async_session() as db:
        crew = await _owned_crew(db, crew_id, user_id)
        if crew is None:
            raise HTTPException(status_code=404, detail="Crew not found")
        crew_name, crew_tasks = crew.name, list(crew.tasks or [])
        configured_agent_ids = [
            str(item.get("agent_id"))
            for item in crew.agents or []
            if isinstance(item, dict) and item.get("agent_id")
        ]
        agent_stmt = select(Agent).where(Agent.user_id == user_id)
        if payload.agent_id:
            agent_stmt = agent_stmt.where(Agent.id == payload.agent_id)
        elif configured_agent_ids:
            agent_stmt = agent_stmt.where(Agent.id.in_(configured_agent_ids))
        else:
            agent_stmt = agent_stmt.order_by(Agent.created_at.desc())
        agent_row = (await db.execute(agent_stmt.limit(1))).scalar_one_or_none()

    if agent_row is None:
        raise HTTPException(status_code=422, detail="No agent configured; create an agent first")
    if not crew_tasks:
        raise HTTPException(status_code=422, detail="Crew has no tasks defined")

    model_registry = di_resolve("ModelRegistry")
    tool_registry = di_resolve("ToolRegistry")
    engine = AgentEngine(model_registry=model_registry, tool_registry=tool_registry)

    task_results, transcript, status, error = await _execute_crew_tasks(
        engine, agent_row, crew_name, crew_tasks, user_id
    )

    run_id = await _record_crew_run(crew_id, data, transcript, task_results, status, error)

    return {
        "id": crew_id,
        "run_id": run_id,
        "status": status,
        "output": transcript,
        "task_results": task_results,
        "error": error,
    }


async def _execute_crew_tasks(
    engine: Any,
    agent_row: Any,
    crew_name: str,
    crew_tasks: list[dict[str, Any]],
    user_id: str,
) -> tuple[list[dict[str, Any]], str, str, str]:
    """Execute all crew tasks sequentially and return results.

    Args:
        engine: The AgentEngine instance.
        agent_row: The agent database entity.
        crew_name: The crew name for context.
        crew_tasks: List of task definitions.

    Returns:
        A tuple of (task_results, transcript, status, error).
    """
    task_results: list[dict[str, Any]] = []
    transcript = ""
    status = "completed"
    error = ""

    try:
        for idx, task in enumerate(crew_tasks):
            description = task.get("description") or task.get("name") or f"Task {idx + 1}"
            prompt = description if not transcript else f"{description}\n\n上一步结果：\n{transcript}"

            session = engine.create_session(
                agent_id=agent_row.id,
                user_id=user_id,
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

    return task_results, transcript, status, error


async def _record_crew_run(
    crew_id: str,
    data: dict[str, Any],
    transcript: str,
    task_results: list[dict[str, Any]],
    status: str,
    error: str,
) -> str:
    """Persist a crew run result and update crew statistics.

    Args:
        crew_id: The crew ID.
        data: The request payload.
        transcript: The concatenated output of all tasks.
        task_results: Individual task results.
        status: The run status.
        error: Error message if failed.

    Returns:
        The run record ID.
    """
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
        return run.id


def _crew_dict(c: Crew) -> dict[str, Any]:
    """Convert a Crew model instance to a response dictionary.

    Args:
        c: The Crew database model instance.

    Returns:
        A dictionary with crew fields for API response.
    """
    return {
        "id": c.id,
        "name": c.name,
        "description": c.description,
        "process": c.process,
        "agents": redact_sensitive_fields(c.agents or []),
        "tasks": redact_sensitive_fields(c.tasks or []),
        "run_count": c.run_count,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }

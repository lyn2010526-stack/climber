"""Workflow CRUD and execution API endpoints."""

from __future__ import annotations

import time
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from sqlalchemy import delete as sa_delete
from sqlalchemy import or_, select

from app.api.v1.common import ok_response, redact_sensitive_fields
from app.core.api_key_crypto import decrypt_api_key
from app.core.di import resolve as di_resolve
from app.core.principal import CurrentPrincipal
from app.schemas.api_v1.workflows import (
    WorkflowCreateRequest,
    WorkflowRunRequest,
    WorkflowUpdateRequest,
)
from app.storage import async_session
from app.storage.models_platform import Workflow, WorkflowRun

logger = structlog.get_logger(__name__)

router = APIRouter()


async def _visible_workflow(db: Any, workflow_id: str, user_id: str) -> Workflow | None:
    """Fetch a workflow the given user may read (owned, or a shared template)."""
    return (
        await db.execute(
            select(Workflow).where(
                Workflow.id == workflow_id,
                or_(Workflow.user_id == user_id, Workflow.is_template == True),  # noqa: E712
            )
        )
    ).scalar_one_or_none()


async def _owned_workflow(db: Any, workflow_id: str, user_id: str) -> Workflow | None:
    """Fetch a workflow owned by the given user, or None."""
    return (
        await db.execute(
            select(Workflow).where(Workflow.id == workflow_id, Workflow.user_id == user_id)
        )
    ).scalar_one_or_none()


@router.get("/workflows")
@router.get("/workflows/", include_in_schema=False)
async def list_workflows(principal: CurrentPrincipal) -> list[dict[str, Any]]:
    """List the current user's workflows plus shared templates, newest first."""
    user_id = principal.subject_id
    async with async_session() as db:
        stmt = select(Workflow)
        if principal.auth_method != "local":
            stmt = stmt.where(or_(Workflow.user_id == user_id, Workflow.is_template == True))  # noqa: E712
        rows = (await db.execute(stmt.order_by(Workflow.created_at.desc()))).scalars().all()
        return [_workflow_dict(w) for w in rows]


@router.post("/workflows")
@router.post("/workflows/", include_in_schema=False)
async def create_workflow(
    payload: WorkflowCreateRequest, principal: CurrentPrincipal
) -> dict[str, Any]:
    """Create a new workflow."""
    data = payload.model_dump()
    user_id = principal.subject_id
    async with async_session() as db:
        wf = Workflow(
            user_id=user_id,
            name=data.get("name") or "Untitled Workflow",
            description=data.get("description", ""),
            nodes=data.get("nodes", []),
            edges=data.get("edges", []),
        )
        db.add(wf)
        await db.commit()
        await db.refresh(wf)
        return _workflow_dict(wf)


@router.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str, principal: CurrentPrincipal) -> dict[str, Any]:
    """Get a single workflow by ID (owned or shared template)."""
    user_id = principal.subject_id
    async with async_session() as db:
        wf = await _visible_workflow(db, workflow_id, user_id)
        if wf is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return _workflow_dict(wf)


@router.put("/workflows/{workflow_id}")
async def update_workflow(
    workflow_id: str, payload: WorkflowUpdateRequest, principal: CurrentPrincipal
) -> dict[str, Any]:
    """Update a workflow's editable fields."""
    data = payload.model_dump(exclude_unset=True)
    user_id = principal.subject_id
    async with async_session() as db:
        wf = await _owned_workflow(db, workflow_id, user_id)
        if wf is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        for field in ("name", "description", "nodes", "edges"):
            if data.get(field) is not None:
                setattr(wf, field, data[field])
        await db.commit()
        await db.refresh(wf)
        return _workflow_dict(wf)


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str, principal: CurrentPrincipal) -> dict[str, bool | str]:
    """Delete a workflow and its run history."""
    user_id = principal.subject_id
    async with async_session() as db:
        wf = await _owned_workflow(db, workflow_id, user_id)
        if wf is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        await db.execute(sa_delete(WorkflowRun).where(WorkflowRun.workflow_id == workflow_id))
        await db.delete(wf)
        await db.commit()
        return ok_response(workflow_id)


@router.post("/workflows/{workflow_id}/run")
async def run_workflow(
    workflow_id: str, payload: WorkflowRunRequest, principal: CurrentPrincipal
) -> dict[str, Any]:
    """Execute a stored workflow, or an ad-hoc graph supplied in the body."""
    from app.storage.database import Agent

    data = payload.model_dump()
    data["workflow_id"] = workflow_id
    started = time.perf_counter()
    user_id = principal.subject_id

    async with async_session() as db:
        wf = await _visible_workflow(db, workflow_id, user_id)
        nodes = data.get("nodes") or (wf.nodes if wf else []) or []
        edges = data.get("edges") or (wf.edges if wf else []) or []

        if not nodes:
            raise HTTPException(status_code=422, detail="Workflow has no nodes to execute")

        referenced_agent_ids = {
            str(agent_id)
            for node in nodes
            if isinstance(node, dict)
            for agent_id in (
                node.get("agent_id"),
                (node.get("data") or {}).get("agent_id")
                if isinstance(node.get("data"), dict)
                else None,
            )
            if agent_id
        }
        if referenced_agent_ids:
            owned_agent_ids = set(
                (
                    await db.execute(
                        select(Agent.id).where(
                            Agent.user_id == user_id,
                            Agent.id.in_(referenced_agent_ids),
                        )
                    )
                ).scalars().all()
            )
            if owned_agent_ids != referenced_agent_ids:
                raise HTTPException(
                    status_code=422,
                    detail="Workflow agent_id must reference an owned agent",
                )

        agent_stmt = select(Agent).where(Agent.user_id == user_id)
        if payload.agent_id:
            agent_stmt = agent_stmt.where(Agent.id == payload.agent_id)
        else:
            agent_stmt = agent_stmt.order_by(Agent.created_at.desc())
        agent = (await db.execute(agent_stmt.limit(1))).scalar_one_or_none()

        if agent is None:
            detail = "Agent not found" if payload.agent_id else "No agent configured; create an agent first"
            raise HTTPException(status_code=422, detail=detail)

    run = WorkflowRun(workflow_id=workflow_id if wf else None, inputs=data.get("inputs", {}))

    try:
        result_payload = await _execute_workflow(wf, agent, nodes, edges, data, started)
    except HTTPException:
        raise
    except Exception as e:
        duration = (time.perf_counter() - started) * 1000
        result_payload = {
            "id": workflow_id,
            "status": "failed",
            "outputs": {},
            "node_results": {},
            "execution_time_ms": duration,
            "error": str(e),
        }

    if wf is not None:
        await _record_workflow_run(run, result_payload)

    return result_payload


async def _execute_workflow(
    wf: Workflow | None,
    agent: Any,
    nodes: list[Any],
    edges: list[Any],
    data: dict[str, Any],
    started: float,
) -> dict[str, Any]:
    """Build and execute a workflow graph.

    Args:
        wf: The stored Workflow entity (optional).
        agent: The first available Agent for model settings.
        nodes: Workflow node definitions.
        edges: Workflow edge definitions.
        data: Request payload with optional inputs.
        started: Perf counter timestamp for duration calculation.

    Returns:
        A dictionary with execution results.
    """
    from app.core.agent_engine import AgentEngine
    from app.core.workflow_executor import build_workflow_from_graph
    from app.workflow.engine import WorkflowEngine

    workflow = build_workflow_from_graph(
        nodes, edges, name=(wf.name if wf else f"Workflow {data.get('workflow_id', '')}")
    )

    model_registry = di_resolve("ModelRegistry")
    tool_registry = di_resolve("ToolRegistry")
    agent_engine = AgentEngine(model_registry=model_registry, tool_registry=tool_registry)
    engine = WorkflowEngine(engine=agent_engine, model_registry=model_registry)

    if agent is not None:
        _apply_agent_settings(engine, agent)

    result = await engine.execute(workflow, user_inputs=data.get("inputs", {}))
    duration = (time.perf_counter() - started) * 1000

    return {
        "id": data.get("workflow_id", ""),
        "status": getattr(result, "status", "completed"),
        "outputs": getattr(result, "outputs", {}),
        "node_results": getattr(result, "node_results", {}),
        "execution_time_ms": getattr(result, "execution_time_ms", duration),
        "error": getattr(result, "error", "") or "",
    }


def _apply_agent_settings(engine: Any, agent: Any) -> None:
    """Apply an agent's model settings to the workflow engine.

    Args:
        engine: The workflow engine instance.
        agent: The agent entity with model configuration.
    """
    for attr, value in (
        ("default_provider", agent.provider),
        ("default_model_id", agent.model_id),
        ("default_api_key", decrypt_api_key(getattr(agent, "api_key_encrypted", "") or "")),
        ("default_base_url", agent.base_url),
    ):
        if hasattr(engine, attr):
            setattr(engine, attr, value)


async def _record_workflow_run(run: WorkflowRun, payload: dict[str, Any]) -> None:
    """Persist a workflow run result and update workflow statistics.

    Args:
        run: The WorkflowRun entity to update.
        payload: The execution result payload.
    """
    async with async_session() as db:
        run.status = payload["status"]
        run.outputs = payload["outputs"]
        run.node_results = payload["node_results"]
        run.error = payload["error"]
        run.duration_ms = payload["execution_time_ms"]
        db.add(run)
        stored = (
            await db.execute(select(Workflow).where(Workflow.id == payload["id"]))
        ).scalar_one_or_none()
        if stored is not None:
            stored.run_count = (stored.run_count or 0) + 1
            stored.last_status = payload["status"]
        await db.commit()
    payload["run_id"] = run.id


@router.get("/workflows/{workflow_id}/runs")
async def list_workflow_runs(
    workflow_id: str, principal: CurrentPrincipal
) -> list[dict[str, Any]]:
    """List the most recent runs for a workflow (up to 50)."""
    user_id = principal.subject_id
    async with async_session() as db:
        wf = await _visible_workflow(db, workflow_id, user_id)
        if wf is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        rows = (
            await db.execute(
                select(WorkflowRun)
                .where(WorkflowRun.workflow_id == workflow_id)
                .order_by(WorkflowRun.created_at.desc())
                .limit(50)
            )
        ).scalars().all()
        return [_run_dict(r) for r in rows]


def _workflow_dict(w: Workflow) -> dict[str, Any]:
    """Convert a Workflow model instance to a response dictionary.

    Args:
        w: The Workflow database model instance.

    Returns:
        A dictionary with workflow fields for API response.
    """
    return {
        "id": w.id,
        "name": w.name,
        "description": w.description,
        "nodes": redact_sensitive_fields(w.nodes or []),
        "edges": redact_sensitive_fields(w.edges or []),
        "is_template": w.is_template,
        "run_count": w.run_count,
        "last_status": w.last_status,
        "created_at": w.created_at.isoformat() if w.created_at else None,
    }


def _run_dict(r: WorkflowRun) -> dict[str, Any]:
    """Convert a WorkflowRun model instance to a response dictionary.

    Args:
        r: The WorkflowRun database model instance.

    Returns:
        A dictionary with run fields for API response.
    """
    return {
        "id": r.id,
        "status": r.status,
        "outputs": r.outputs,
        "error": r.error,
        "duration_ms": r.duration_ms,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }

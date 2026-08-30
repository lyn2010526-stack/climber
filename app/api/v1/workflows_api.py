"""Workflow and crew endpoints.

Split out of the former monolithic generic API module (pure move refactor).
Routes are registered with and without a trailing slash because the app runs
with redirect_slashes=False.
"""

from __future__ import annotations

import time
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import delete as sa_delete
from sqlalchemy import select

from app.api.v1._shared import DEFAULT_USER, _payload
from app.core.api_key_crypto import decrypt_api_key
from app.core.auth import get_current_user
from app.core.di import resolve as di_resolve
from app.storage import async_session
from app.storage.models_platform import Crew, CrewRun, Workflow, WorkflowRun

router = APIRouter(dependencies=[Depends(get_current_user)])
logger = structlog.get_logger()

# ─── Workflows ──────────────────────────────────────────────────────────────

def _workflow_dict(w: Workflow) -> dict[str, Any]:
    return {
        "id": w.id,
        "name": w.name,
        "description": w.description,
        "nodes": w.nodes or [],
        "edges": w.edges or [],
        "is_template": w.is_template,
        "run_count": w.run_count,
        "last_status": w.last_status,
        "created_at": w.created_at.isoformat() if w.created_at else None,
    }


@router.get("/workflows")
@router.get("/workflows/")
async def list_workflows(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    async with async_session() as db:
        rows = (
            await db.execute(
                select(Workflow)
                .where(Workflow.is_template == False)
                .order_by(Workflow.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        ).scalars().all()
        return [_workflow_dict(w) for w in rows]


@router.post("/workflows")
@router.post("/workflows/")
async def create_workflow(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    async with async_session() as db:
        wf = Workflow(
            user_id=DEFAULT_USER,
            name=data.get("name") or "Untitled Workflow",
            description=data.get("description", ""),
            nodes=data.get("nodes", []),
            edges=data.get("edges", []),
        )
        db.add(wf)
        await db.commit()
        await db.refresh(wf)
        return _workflow_dict(wf)


@router.get("/workflows/node-types")
async def list_workflow_node_types() -> list[dict[str, Any]]:
    """Return serializable canvas metadata for every registered node type."""
    from app.workflow.registry import node_registry

    return [definition.model_dump() for definition in node_registry.list_types()]


@router.post("/workflows/nodes/run")
async def run_workflow_node(
    request: Request,
    user_id: str = Depends(get_current_user),
) -> dict[str, Any]:
    """Run one canvas node without creating or mutating a stored workflow."""
    from app.core.agent_engine import AgentEngine
    from app.core.workflow_executor import build_workflow_from_graph
    from app.workflow.engine import WorkflowEngine

    data = await _payload(request)
    node_data = data.get("node")
    if (
        not isinstance(node_data, dict)
        or not isinstance(node_data.get("id"), str)
        or not node_data["id"].strip()
        or not isinstance(node_data.get("type"), str)
        or not node_data["type"].strip()
    ):
        raise HTTPException(status_code=422, detail={"errors": ["node.id and node.type are required"]})
    if "data" in node_data and not isinstance(node_data["data"], dict):
        raise HTTPException(status_code=422, detail={"errors": ["node.data must be an object"]})
    inputs = data.get("inputs", {})
    if not isinstance(inputs, dict):
        raise HTTPException(status_code=422, detail={"errors": ["inputs must be an object"]})

    from app.workflow.registry import node_registry

    canvas_type = str(node_data["type"])
    if node_registry.get(canvas_type) is None:
        return {
            "node_id": node_data["id"],
            "status": "failed",
            "output": None,
            "error": f"Unknown workflow node type: {canvas_type}",
            "execution_time_ms": 0.0,
        }
    try:
        workflow = build_workflow_from_graph([node_data], [])
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"errors": [str(exc)]}) from exc
    node = workflow.nodes[0]
    from app.workflow import NodeType

    if node.type in {NodeType.START, NodeType.END}:
        return {
            "node_id": node.id,
            "status": "completed",
            "output": inputs,
            "error": "",
            "execution_time_ms": 0.0,
        }
    model_registry = di_resolve("ModelRegistry")
    tool_registry = di_resolve("ToolRegistry")
    agent_engine = AgentEngine(model_registry=model_registry, tool_registry=tool_registry)
    engine = WorkflowEngine(engine=agent_engine, model_registry=model_registry)
    return await engine.execute_single_node(
        node,
        inputs=inputs,
        user_id=user_id,
    )


@router.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str) -> dict[str, Any]:
    async with async_session() as db:
        wf = (await db.execute(select(Workflow).where(Workflow.id == workflow_id))).scalar_one_or_none()
        if wf is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return _workflow_dict(wf)


@router.put("/workflows/{workflow_id}")
async def update_workflow(workflow_id: str, request: Request) -> dict[str, Any]:
    data = await _payload(request)
    async with async_session() as db:
        wf = (await db.execute(select(Workflow).where(Workflow.id == workflow_id))).scalar_one_or_none()
        if wf is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        for field in ("name", "description", "nodes", "edges"):
            if data.get(field) is not None:
                setattr(wf, field, data[field])
        await db.commit()
        await db.refresh(wf)
        return _workflow_dict(wf)


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str) -> dict:
    async with async_session() as db:
        wf = (await db.execute(select(Workflow).where(Workflow.id == workflow_id))).scalar_one_or_none()
        if wf is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        await db.execute(sa_delete(WorkflowRun).where(WorkflowRun.workflow_id == workflow_id))
        await db.delete(wf)
        await db.commit()
        return {"ok": True, "deleted": workflow_id}


@router.post("/workflows/{workflow_id}/run")
async def run_workflow(
    workflow_id: str,
    request: Request,
    user_id: str = Depends(get_current_user),
) -> dict[str, Any]:
    """Execute a stored workflow, or an ad-hoc graph supplied in the body."""
    from app.core.agent_engine import AgentEngine
    from app.core.workflow_executor import build_workflow_from_graph, validate_workflow_graph
    from app.storage.database import Agent
    from app.workflow.engine import WorkflowEngine

    data = await _payload(request)
    started = time.perf_counter()

    async with async_session() as db:
        wf = (await db.execute(select(Workflow).where(Workflow.id == workflow_id))).scalar_one_or_none()

        # Prefer nodes/edges from the request (live canvas), else the stored graph
        nodes = data.get("nodes") or (wf.nodes if wf else []) or []
        edges = data.get("edges") or (wf.edges if wf else []) or []

        if not nodes:
            raise HTTPException(status_code=422, detail="Workflow has no nodes to execute")

        try:
            validation = validate_workflow_graph(nodes, edges)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail={"errors": [str(exc)]},
            ) from None
        if not validation["valid"]:
            raise HTTPException(status_code=422, detail={"errors": validation["errors"]})

        agent = (await db.execute(select(Agent).limit(1))).scalar_one_or_none()

    run = WorkflowRun(workflow_id=workflow_id if wf else None, inputs=data.get("inputs", {}))

    try:
        workflow = build_workflow_from_graph(nodes, edges, name=(wf.name if wf else f"Workflow {workflow_id}"))
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"errors": [str(exc)]},
        ) from None

    try:
        model_registry = di_resolve("ModelRegistry")
        tool_registry = di_resolve("ToolRegistry")
        agent_engine = AgentEngine(model_registry=model_registry, tool_registry=tool_registry)
        engine = WorkflowEngine(engine=agent_engine, model_registry=model_registry)

        # Pass the configured agent's model settings through to the engine
        if agent is not None:
            for attr, value in (
                ("default_provider", agent.provider),
                ("default_model_id", agent.model_id),
                ("default_api_key", decrypt_api_key(getattr(agent, "api_key_encrypted", "") or "")),
                ("default_base_url", agent.base_url),
            ):
                if hasattr(engine, attr):
                    setattr(engine, attr, value)

        result = await engine.execute(
            workflow,
            user_inputs=data.get("inputs", {}),
            user_id=user_id,
        )
        duration = (time.perf_counter() - started) * 1000

        payload = {
            "id": workflow_id,
            "status": getattr(result, "status", "completed"),
            "outputs": getattr(result, "outputs", {}),
            "node_results": getattr(result, "node_results", {}),
            "execution_time_ms": getattr(result, "execution_time_ms", duration),
            "error": getattr(result, "error", "") or "",
        }
    except HTTPException:
        raise
    except Exception as e:
        duration = (time.perf_counter() - started) * 1000
        payload = {
            "id": workflow_id,
            "status": "failed",
            "outputs": {},
            "node_results": {},
            "execution_time_ms": duration,
            "error": str(e),
        }

    # Record the run and update workflow stats
    if wf is not None:
        async with async_session() as db:
            run.status = payload["status"]
            run.outputs = payload["outputs"]
            run.node_results = payload["node_results"]
            run.error = payload["error"]
            run.duration_ms = payload["execution_time_ms"]
            db.add(run)
            stored = (await db.execute(select(Workflow).where(Workflow.id == workflow_id))).scalar_one_or_none()
            if stored is not None:
                stored.run_count = (stored.run_count or 0) + 1
                stored.last_status = payload["status"]
            await db.commit()
        payload["run_id"] = run.id

    return payload


@router.get("/workflows/{workflow_id}/runs")
async def list_workflow_runs(
    workflow_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    async with async_session() as db:
        rows = (
            await db.execute(
                select(WorkflowRun)
                .where(WorkflowRun.workflow_id == workflow_id)
                .order_by(WorkflowRun.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        ).scalars().all()
        return [
            {
                "id": r.id,
                "status": r.status,
                "outputs": r.outputs,
                "error": r.error,
                "duration_ms": r.duration_ms,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]


# ─── Crews ──────────────────────────────────────────────────────────────────

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
    """Run a crew's tasks sequentially through the agent engine."""
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
            prompt = description if not transcript else f"{description}\n\n上一步结果：\n{transcript}"

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
        run_id = run.id

    return {
        "id": crew_id,
        "run_id": run_id,
        "status": status,
        "output": transcript,
        "task_results": task_results,
        "error": error,
    }

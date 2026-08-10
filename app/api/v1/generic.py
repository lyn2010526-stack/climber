"""Generic API endpoints backed by real database persistence.

Every endpoint here performs real reads/writes. Request bodies accept either
a flat object (what the frontend sends) or a {"data": {...}} envelope.
Routes are registered with and without a trailing slash because the app runs
with redirect_slashes=False.
"""

from __future__ import annotations

import asyncio
import json
import structlog
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from starlette.websockets import WebSocket
from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.storage import async_session
from app.storage.models_groups import AgentGroup, AgentGroupMember, AgentGroupMessage, AgentGroupTask
from app.storage.models_platform import (
    Cluster,
    Crew,
    CrewRun,
    Skill,
    Trace,
    Workflow,
    WorkflowRun,
)
from app.storage.models_plugins import PluginRecord
from app.core.api_key_crypto import decrypt_api_key, encrypt_api_key
from app.core.di import resolve as di_resolve

router = APIRouter()
logger = structlog.get_logger()

DEFAULT_USER = "default-user"


async def _payload(request: Request) -> dict[str, Any]:
    """Read a JSON body tolerantly: flat object or {"data": {...}} envelope."""
    try:
        raw = await request.json()
    except Exception:
        return {}
    if not isinstance(raw, dict):
        return {}
    inner = raw.get("data")
    if isinstance(inner, dict):
        return inner
    return raw


# ─── Agents ─────────────────────────────────────────────────────────────────

@router.get("/agents")
@router.get("/agents/")
async def list_agents() -> list[dict[str, Any]]:
    from app.storage.database import Agent

    async with async_session() as db:
        rows = (await db.execute(select(Agent).order_by(Agent.created_at.desc()))).scalars().all()
        return [
            {
                "id": a.id,
                "name": a.name,
                "description": getattr(a, "description", "") or "",
                "provider": a.provider,
                "model_id": a.model_id,
                "system_prompt": getattr(a, "system_prompt", "") or "",
                "base_url": a.base_url,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in rows
        ]


@router.post("/agents")
@router.post("/agents/")
async def create_agent(request: Request) -> dict[str, Any]:
    from app.storage.database import Agent

    data = await _payload(request)
    if not data.get("name"):
        raise HTTPException(status_code=422, detail="name is required")

    async with async_session() as db:
        agent = Agent(
            user_id=DEFAULT_USER,
            name=data["name"],
            provider=data.get("provider", "openai"),
            model_id=data.get("model_id", "gpt-4o-mini"),
            base_url=data.get("base_url"),
            api_key_encrypted=encrypt_api_key(
                data.get("api_key") or data.get("api_key_encrypted") or ""
            ) or None,
        )
        for field in ("description", "system_prompt", "tool_ids", "skill_ids"):
            if hasattr(agent, field) and data.get(field) is not None:
                setattr(agent, field, data[field])
        if not getattr(agent, "tool_ids", None):
            tool_registry = di_resolve("ToolRegistry")
            agent.tool_ids = [t.name for t in tool_registry.list_tools()]
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        return {
            "id": agent.id,
            "name": agent.name,
            "provider": agent.provider,
            "model_id": agent.model_id,
            "base_url": agent.base_url,
        }


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str) -> dict[str, Any]:
    from app.storage.database import Agent

    async with async_session() as db:
        agent = (await db.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return {
            "id": agent.id,
            "name": agent.name,
            "description": getattr(agent, "description", "") or "",
            "provider": agent.provider,
            "model_id": agent.model_id,
            "system_prompt": getattr(agent, "system_prompt", "") or "",
            "base_url": agent.base_url,
            "tool_ids": getattr(agent, "tool_ids", []) or [],
            "skill_ids": getattr(agent, "skill_ids", []) or [],
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
        }


@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str) -> dict:
    from app.storage.database import Agent

    async with async_session() as db:
        agent = (await db.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        await db.delete(agent)
        await db.commit()
        return {"ok": True, "deleted": agent_id}


# ─── Tools ──────────────────────────────────────────────────────────────────

@router.get("/tools")
@router.get("/tools/")
async def list_tools() -> list[dict[str, Any]]:
    import app.tools.builtins  # noqa: F401  ensures builtin tools are registered
    tool_registry = di_resolve("ToolRegistry")

    return [
        {"name": t.name, "description": t.description, "parameters": t.parameters}
        for t in tool_registry.list_tools()
    ]


# ─── Models ─────────────────────────────────────────────────────────────────

@router.get("/models")
@router.get("/models/")
async def list_models() -> list[dict[str, Any]]:
    """Return known models per provider, plus locally discovered Ollama models."""
    from app.models.registry import MODEL_ALIASES, ModelRegistry

    model_registry = di_resolve("ModelRegistry")
    models: list[dict[str, Any]] = []
    seen: set[str] = set()

    # Build from registry's known aliases (deduplicated by provider:model_id)
    for alias, (provider, model_id) in MODEL_ALIASES.items():
        key = f"{provider}:{model_id}"
        if key not in seen:
            seen.add(key)
            models.append({"provider": provider, "model_id": model_id, "label": alias})

    # Add any user-registered models from the registry
    for m in model_registry.list_models():
        key = f"{m['provider']}:{m['model_id']}"
        if key not in seen:
            seen.add(key)
            models.append({"provider": m["provider"], "model_id": m["model_id"], "label": m["model_id"]})

    # Discover local Ollama models when the daemon is reachable
    try:
        import httpx

        from app.config import settings

        base = getattr(settings, "ollama_base_url", "http://localhost:11434")
        async with httpx.AsyncClient(timeout=1.5) as client:
            resp = await client.get(f"{base}/api/tags")
            if resp.status_code == 200:
                for m in resp.json().get("models", []):
                    models.append(
                        {"provider": "ollama", "model_id": m.get("name", ""), "label": f"{m.get('name','')} (local)"}
                    )
    except Exception as e:
        logger.warning("generic.list_models_ollama_discovery", error=str(e))
    return models


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
async def list_workflows() -> list[dict[str, Any]]:
    async with async_session() as db:
        rows = (
            await db.execute(
                select(Workflow).where(Workflow.is_template == False).order_by(Workflow.created_at.desc())  # noqa: E712
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
async def run_workflow(workflow_id: str, request: Request) -> dict[str, Any]:
    """Execute a stored workflow, or an ad-hoc graph supplied in the body."""
    from app.core.agent_engine import AgentEngine
    from app.core.workflow_executor import build_workflow_from_graph
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

        agent = (await db.execute(select(Agent).limit(1))).scalar_one_or_none()

    run = WorkflowRun(workflow_id=workflow_id if wf else None, inputs=data.get("inputs", {}))

    try:
        workflow = build_workflow_from_graph(nodes, edges, name=(wf.name if wf else f"Workflow {workflow_id}"))

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

        result = await engine.execute(workflow, user_inputs=data.get("inputs", {}))
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
async def list_workflow_runs(workflow_id: str) -> list[dict[str, Any]]:
    async with async_session() as db:
        rows = (
            await db.execute(
                select(WorkflowRun)
                .where(WorkflowRun.workflow_id == workflow_id)
                .order_by(WorkflowRun.created_at.desc())
                .limit(50)
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
async def list_crews() -> list[dict[str, Any]]:
    async with async_session() as db:
        rows = (await db.execute(select(Crew).order_by(Crew.created_at.desc()))).scalars().all()
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


# ─── Stats ──────────────────────────────────────────────────────────────────

@router.get("/stats")
@router.get("/stats/")
async def get_stats() -> dict[str, Any]:
    from app.storage.database import Agent, ApiKey, Message, Session, UsageLog

    async with async_session() as db:
        async def count(model) -> int:
            return (await db.execute(select(func.count()).select_from(model))).scalar() or 0

        total_tokens = (await db.execute(select(func.coalesce(func.sum(UsageLog.total_tokens), 0)))).scalar() or 0

        return {
            "total_users": 1,
            "total_agents": await count(Agent),
            "total_api_keys": await count(ApiKey),
            "total_sessions": await count(Session),
            "total_messages": await count(Message),
            "total_tokens": int(total_tokens),
            "total_workflows": await count(Workflow),
            "total_crews": await count(Crew),
        }


@router.get("/profile")
@router.get("/profile/")
async def get_profile() -> dict[str, Any]:
    return {"id": DEFAULT_USER, "display_name": "Local User", "email": "local@localhost", "is_admin": True}


# ─── Skills ─────────────────────────────────────────────────────────────────

def _skill_dict(s: Skill) -> dict[str, Any]:
    return {
        "id": s.id,
        "name": s.name,
        "description": s.description,
        "category": s.category,
        "prompt_template": s.prompt_template,
        "tools": s.tools or [],
        "is_enabled": s.is_enabled,
        "use_count": s.use_count,
    }


@router.get("/skills")
@router.get("/skills/")
async def list_skills() -> list[dict[str, Any]]:
    async with async_session() as db:
        rows = (await db.execute(select(Skill).order_by(Skill.created_at.desc()))).scalars().all()
        return [_skill_dict(s) for s in rows]


@router.post("/skills")
@router.post("/skills/")
async def create_skill(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    if not data.get("name"):
        raise HTTPException(status_code=422, detail="name is required")
    async with async_session() as db:
        skill = Skill(
            user_id=DEFAULT_USER,
            name=data["name"],
            description=data.get("description", ""),
            category=data.get("category", "general"),
            prompt_template=data.get("prompt_template", ""),
            tools=data.get("tools", []),
        )
        db.add(skill)
        await db.commit()
        await db.refresh(skill)
        return _skill_dict(skill)


async def _set_skill_enabled(skill_id: str, enabled: bool) -> dict:
    async with async_session() as db:
        skill = (await db.execute(select(Skill).where(Skill.id == skill_id))).scalar_one_or_none()
        if skill is None:
            raise HTTPException(status_code=404, detail="Skill not found")
        skill.is_enabled = enabled
        await db.commit()
        return {"ok": True, "id": skill_id, "is_enabled": enabled}


@router.post("/skills/{skill_id}/enable")
async def enable_skill(skill_id: str) -> dict:
    return await _set_skill_enabled(skill_id, True)


@router.post("/skills/{skill_id}/disable")
async def disable_skill(skill_id: str) -> dict:
    return await _set_skill_enabled(skill_id, False)


@router.delete("/skills/{skill_id}")
async def delete_skill(skill_id: str) -> dict:
    async with async_session() as db:
        skill = (await db.execute(select(Skill).where(Skill.id == skill_id))).scalar_one_or_none()
        if skill is None:
            raise HTTPException(status_code=404, detail="Skill not found")
        await db.delete(skill)
        await db.commit()
        return {"ok": True, "deleted": skill_id}


# ─── Cluster ────────────────────────────────────────────────────────────────

@router.get("/cluster")
@router.get("/cluster/")
async def list_cluster_nodes() -> list[dict[str, Any]]:
    async with async_session() as db:
        rows = (await db.execute(select(Cluster).order_by(Cluster.created_at.desc()))).scalars().all()
        return [
            {
                "id": n.id,
                "name": n.name,
                "endpoint": n.endpoint,
                "role": n.role,
                "status": n.status,
                "capabilities": n.capabilities or [],
                "last_heartbeat": n.last_heartbeat.isoformat() if n.last_heartbeat else None,
            }
            for n in rows
        ]


@router.post("/cluster")
@router.post("/cluster/")
@router.post("/cluster/create")
async def create_cluster_node(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    if not data.get("name"):
        raise HTTPException(status_code=422, detail="name is required")
    async with async_session() as db:
        node = Cluster(
            name=data["name"],
            endpoint=data.get("endpoint", ""),
            role=data.get("role", "worker"),
            status=data.get("status", "offline"),
            capabilities=data.get("capabilities", []),
        )
        db.add(node)
        await db.commit()
        await db.refresh(node)
        return {"id": node.id, "name": node.name, "endpoint": node.endpoint, "status": node.status}


@router.get("/cluster/status")
async def get_cluster_status() -> dict[str, Any]:
    async with async_session() as db:
        rows = (await db.execute(select(Cluster))).scalars().all()
        online = [n for n in rows if n.status == "online"]
        return {
            "status": "ok",
            "total_nodes": len(rows),
            "online_nodes": len(online),
            "nodes": [{"id": n.id, "name": n.name, "status": n.status, "role": n.role} for n in rows],
        }


@router.get("/cluster/stats")
@router.get("/cluster/stats/")
async def get_cluster_stats() -> dict[str, Any]:
    async with async_session() as db:
        rows = (await db.execute(select(Cluster))).scalars().all()
        total = len(rows)
        online = sum(1 for n in rows if n.status == "online")
        offline = total - online
        roles: dict[str, int] = {}
        for n in rows:
            roles[n.role] = roles.get(n.role, 0) + 1
        return {
            "total": total,
            "online": online,
            "offline": offline,
            "roles": roles,
        }


@router.delete("/cluster/{node_id}")
async def delete_cluster_node(node_id: str) -> dict:
    async with async_session() as db:
        node = (await db.execute(select(Cluster).where(Cluster.id == node_id))).scalar_one_or_none()
        if node is None:
            raise HTTPException(status_code=404, detail="Node not found")
        await db.delete(node)
        await db.commit()
        return {"ok": True, "deleted": node_id}


# ─── Traces ─────────────────────────────────────────────────────────────────

@router.get("/traces")
@router.get("/traces/")
async def list_traces(limit: int = 100) -> list[dict[str, Any]]:
    async with async_session() as db:
        rows = (
            await db.execute(select(Trace).order_by(Trace.created_at.desc()).limit(limit))
        ).scalars().all()
        return [
            {
                "id": t.id,
                "session_id": t.session_id,
                "trace_type": t.trace_type,
                "name": t.name,
                "status": t.status,
                "duration_ms": t.duration_ms,
                "tokens_used": t.tokens_used,
                "error": t.error,
                "spans": t.spans or [],
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in rows
        ]


@router.get("/traces/{trace_id}")
async def get_trace(trace_id: str) -> dict[str, Any]:
    async with async_session() as db:
        t = (await db.execute(select(Trace).where(Trace.id == trace_id))).scalar_one_or_none()
        if t is None:
            raise HTTPException(status_code=404, detail="Trace not found")
        return {
            "id": t.id,
            "session_id": t.session_id,
            "trace_type": t.trace_type,
            "name": t.name,
            "status": t.status,
            "input_data": t.input_data,
            "output_data": t.output_data,
            "spans": t.spans or [],
            "duration_ms": t.duration_ms,
            "tokens_used": t.tokens_used,
            "error": t.error,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }


# ─── Plugins ────────────────────────────────────────────────────────────────

def _get_marketplace() -> list[dict[str, Any]]:
    """Return plugin marketplace catalog from settings."""
    from app.config import settings
    return list(settings.plugin_marketplace)


def _plugin_dict(p: PluginRecord) -> dict[str, Any]:
    return {
        "id": p.id,
        "plugin_key": p.plugin_key,
        "name": p.name,
        "description": p.description,
        "category": p.category,
        "version": p.version,
        "author": p.author,
        "type": p.type,
        "source": p.source,
        "status": p.status,
        "is_installed": p.status in ("installed", "enabled", "disabled"),
        "is_enabled": p.status == "enabled",
    }


@router.get("/plugins")
@router.get("/plugins/")
async def list_plugins(type: str = "") -> list[dict[str, Any]]:
    async with async_session() as db:
        stmt = select(PluginRecord).order_by(PluginRecord.installed_at.desc())
        if type:
            stmt = stmt.where(PluginRecord.category == type)
        rows = (await db.execute(stmt)).scalars().all()
        return [_plugin_dict(p) for p in rows]


@router.get("/plugins/marketplace")
@router.get("/plugins/marketplace/")
async def get_marketplace() -> list[dict[str, Any]]:
    async with async_session() as db:
        installed = {
            p.plugin_key
            for p in (await db.execute(select(PluginRecord))).scalars().all()
            if p.plugin_key
        }
    return [{**item, "is_installed": item["plugin_key"] in installed} for item in _get_marketplace()]


@router.get("/plugins/categories")
@router.get("/plugins/categories/")
async def get_plugin_categories() -> list[str]:
    async with async_session() as db:
        rows = (await db.execute(select(PluginRecord.category).distinct())).scalars().all()
    return sorted({*(r for r in (rows or []) if r), *(m["category"] for m in _get_marketplace())})


@router.post("/plugins/{plugin_key}/install")
async def install_plugin(plugin_key: str, request: Request) -> dict[str, Any]:
    entry = next((m for m in _get_marketplace() if m["plugin_key"] == plugin_key), None)
    data = await _payload(request)
    async with async_session() as db:
        existing = (
            await db.execute(select(PluginRecord).where(PluginRecord.plugin_key == plugin_key))
        ).scalars().first()
        if existing is not None:
            existing.status = "installed"
            await db.commit()
            await db.refresh(existing)
            return _plugin_dict(existing)

        plugin = PluginRecord(
            plugin_key=plugin_key,
            name=(entry or data).get("name", plugin_key),
            description=(entry or data).get("description", ""),
            category=(entry or data).get("category", "general"),
            version=(entry or data).get("version", "1.0.0"),
            author=(entry or data).get("author", ""),
            type=data.get("type", "skill"),
            source="marketplace" if entry else "custom",
            config=data.get("config", {}),
            status="installed",
        )
        db.add(plugin)
        await db.commit()
        await db.refresh(plugin)
        return _plugin_dict(plugin)


async def _find_plugin(db, plugin_id: str) -> PluginRecord | None:
    return (
        await db.execute(
            select(PluginRecord).where(
                (PluginRecord.id == plugin_id) | (PluginRecord.plugin_key == plugin_id)
            )
        )
    ).scalars().first()


async def _set_plugin_enabled(plugin_id: str, enabled: bool) -> dict:
    async with async_session() as db:
        plugin = await _find_plugin(db, plugin_id)
        if plugin is None:
            raise HTTPException(status_code=404, detail="Plugin not found")
        plugin.status = "enabled" if enabled else "disabled"
        await db.commit()
        return {"ok": True, "id": plugin.id, "is_enabled": enabled, "status": plugin.status}


@router.post("/plugins/{plugin_id}/enable")
async def enable_plugin(plugin_id: str) -> dict:
    return await _set_plugin_enabled(plugin_id, True)


@router.post("/plugins/{plugin_id}/disable")
async def disable_plugin(plugin_id: str) -> dict:
    return await _set_plugin_enabled(plugin_id, False)


@router.delete("/plugins/{plugin_id}")
@router.post("/plugins/{plugin_id}/uninstall")
async def uninstall_plugin(plugin_id: str) -> dict:
    async with async_session() as db:
        plugin = await _find_plugin(db, plugin_id)
        if plugin is None:
            raise HTTPException(status_code=404, detail="Plugin not found")
        await db.delete(plugin)
        await db.commit()
        return {"ok": True, "deleted": plugin_id}


@router.get("/plugins/{plugin_id}/status")
async def get_plugin_status(plugin_id: str) -> dict[str, Any]:
    async with async_session() as db:
        plugin = await _find_plugin(db, plugin_id)
        if plugin is None:
            raise HTTPException(status_code=404, detail="Plugin not found")
        return {
            "id": plugin.id,
            "status": plugin.status,
            "is_installed": plugin.status in ("installed", "enabled", "disabled"),
        }


@router.post("/plugins/import")
async def import_plugin(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    key = data.get("plugin_key") or data.get("name")
    if not key:
        raise HTTPException(status_code=422, detail="plugin_key or name is required")
    async with async_session() as db:
        plugin = PluginRecord(
            plugin_key=key,
            name=data.get("name", key),
            description=data.get("description", ""),
            category=data.get("category", "general"),
            version=data.get("version", "1.0.0"),
            author=data.get("author", ""),
            type=data.get("type", "skill"),
            source="custom",
            source_url=data.get("source_url"),
            config=data.get("config", {}),
            status="installed",
        )
        db.add(plugin)
        await db.commit()
        await db.refresh(plugin)
        return _plugin_dict(plugin)


# ─── Groups ─────────────────────────────────────────────────────────────────

from app.storage.models_groups import AgentGroup, AgentGroupMember, AgentGroupTask


def _group_dict(g: AgentGroup, member_count: int = 0, members: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "id": g.id,
        "name": g.name,
        "description": g.description,
        "topic": g.topic,
        "status": g.status,
        "max_rounds": g.max_rounds,
        "process_type": getattr(g, "process_type", "sequential"),
        "manager_agent_id": getattr(g, "manager_agent_id", None),
        "manager_llm": getattr(g, "manager_llm", None),
        "member_count": member_count,
        "members": members or [],
        "created_at": g.created_at.isoformat() if g.created_at else "",
    }


@router.get("/groups")
@router.get("/groups/")
async def list_groups() -> list[dict[str, Any]]:
    async with async_session() as db:
        rows = (await db.execute(
            select(AgentGroup).options(selectinload(AgentGroup.members)).order_by(AgentGroup.created_at.desc())
        )).scalars().all()
        result = []
        for g in rows:
            members = [
                {
                    "id": m.id,
                    "agent_id": m.agent_id,
                    "role": m.role,
                    "status": m.status,
                    "is_worker": m.is_worker,
                    "model_provider": m.model_provider,
                    "model_id": m.model_id,
                    "tools": m.tools,
                    "message_count": m.message_count,
                    "last_active": m.last_active.isoformat() if m.last_active else None,
                }
                for m in g.members
            ]
            result.append(_group_dict(g, member_count=len(members), members=members))
        return result


@router.post("/groups")
@router.post("/groups/")
async def create_group(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    async with async_session() as db:
        group = AgentGroup(
            user_id=DEFAULT_USER,
            name=data.get("name", "New Group"),
            description=data.get("description", ""),
            topic=data.get("topic", ""),
            status=data.get("status", "active"),
            max_rounds=int(data.get("max_rounds") or 10),
            process_type=data.get("process_type", "sequential"),
        )
        logger.debug("group.process_type", process_type=group.process_type)
        db.add(group)
        await db.commit()
        await db.refresh(group)

        # Auto-add default members if template is specified
        template = data.get("template")
        if template == "default":
            default_members = [
                {"agent_id": "planner-1", "role": "planner", "model_provider": "stepfun", "model_id": "step-3.5-flash"},
                {"agent_id": "executor-1", "role": "executor", "model_provider": "stepfun", "model_id": "step-3.5-flash"},
                {"agent_id": "reviewer-1", "role": "reviewer", "model_provider": "stepfun", "model_id": "step-3.5-flash"},
            ]
            for m in default_members:
                member = AgentGroupMember(
                    group_id=group.id,
                    agent_id=m["agent_id"],
                    role=m["role"],
                    model_provider=m["model_provider"],
                    model_id=m["model_id"],
                )
                db.add(member)
            await db.commit()

        # Reload with members for response
        group = (await db.execute(
            select(AgentGroup).where(AgentGroup.id == group.id).options(selectinload(AgentGroup.members))
        )).scalars().first()
        members = [
            {
                "id": m.id,
                "agent_id": m.agent_id,
                "role": m.role,
                "status": m.status,
                "is_worker": m.is_worker,
                "model_provider": m.model_provider,
                "model_id": m.model_id,
                "tools": m.tools,
                "message_count": m.message_count,
                "last_active": m.last_active.isoformat() if m.last_active else None,
            }
            for m in (group.members if group else [])
        ]
        return _group_dict(group, member_count=len(members), members=members)


@router.get("/groups/{group_id}")
async def get_group(group_id: str) -> dict[str, Any]:
    async with async_session() as db:
        group = (await db.execute(
            select(AgentGroup).where(AgentGroup.id == group_id).options(selectinload(AgentGroup.members))
        )).scalars().first()
        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")
        members = [
            {
                "id": m.id,
                "agent_id": m.agent_id,
                "role": m.role,
                "status": m.status,
                "is_worker": m.is_worker,
                "model_provider": m.model_provider,
                "model_id": m.model_id,
                "tools": m.tools,
                "message_count": m.message_count,
                "last_active": m.last_active.isoformat() if m.last_active else None,
            }
            for m in group.members
        ]
        return _group_dict(group, member_count=len(members), members=members)


@router.delete("/groups/{group_id}")
async def delete_group(group_id: str) -> dict[str, Any]:
    async with async_session() as db:
        group = (await db.execute(select(AgentGroup).where(AgentGroup.id == group_id))).scalars().first()
        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")
        await db.delete(group)
        await db.commit()
        return {"ok": True}


@router.post("/groups/{group_id}/members")
async def add_group_member(group_id: str, request: Request) -> dict[str, Any]:
    data = await _payload(request)
    async with async_session() as db:
        group = (await db.execute(select(AgentGroup).where(AgentGroup.id == group_id))).scalars().first()
        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")
        member = AgentGroupMember(
            group_id=group_id,
            agent_id=data.get("agent_id", ""),
            role=data.get("role", "participant"),
            model_provider=data.get("model_provider"),
            model_id=data.get("model_id"),
            api_key_encrypted=data.get("api_key_encrypted"),
            tools=data.get("tools", []),
            is_worker=bool(data.get("is_worker", False)),
        )
        db.add(member)
        await db.commit()
        await db.refresh(member)
        return {
            "id": member.id,
            "group_id": member.group_id,
            "agent_id": member.agent_id,
            "role": member.role,
            "status": member.status,
            "is_worker": member.is_worker,
        }


@router.get("/groups/{group_id}/messages")
async def list_group_messages(group_id: str, limit: int = 50) -> dict[str, Any]:
    async with async_session() as db:
        rows = (
            await db.execute(
                select(AgentGroupMessage)
                .where(AgentGroupMessage.group_id == group_id)
                .order_by(AgentGroupMessage.created_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        return {
            "messages": [
                {
                    "id": m.id,
                    "sender_id": m.sender_id,
                    "sender_name": m.sender_name,
                    "content": m.content,
                    "message_type": m.message_type,
                    "created_at": m.created_at.isoformat() if m.created_at else "",
                }
                for m in rows
            ]
        }


@router.delete("/groups/{group_id}/members/{member_id}")
async def remove_group_member(group_id: str, member_id: str) -> dict[str, Any]:
    async with async_session() as db:
        member = (
            await db.execute(
                select(AgentGroupMember).where(
                    AgentGroupMember.id == member_id,
                    AgentGroupMember.group_id == group_id,
                )
            )
        ).scalar_one_or_none()
        if member is None:
            raise HTTPException(status_code=404, detail="Member not found")
        await db.delete(member)
        await db.commit()
        return {"ok": True, "deleted": member_id}


@router.patch("/groups/{group_id}/members/{member_id}")
async def update_group_member(group_id: str, member_id: str, request: Request) -> dict[str, Any]:
    data = await _payload(request)
    async with async_session() as db:
        member = (
            await db.execute(
                select(AgentGroupMember).where(
                    AgentGroupMember.id == member_id,
                    AgentGroupMember.group_id == group_id,
                )
            )
        ).scalar_one_or_none()
        if member is None:
            raise HTTPException(status_code=404, detail="Member not found")
        if "role" in data:
            member.role = data["role"]
        if "status" in data:
            member.status = data["status"]
        if "is_worker" in data:
            member.is_worker = bool(data["is_worker"])
        if "current_task_id" in data:
            member.current_task_id = data["current_task_id"]
        await db.commit()
        return {
            "id": member.id,
            "role": member.role,
            "status": member.status,
            "is_worker": member.is_worker,
            "current_task_id": member.current_task_id,
        }


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
    async with async_session() as db:
        task = AgentGroupTask(
            group_id=data.get("group_id", ""),
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
async def run_task(task_id: str) -> dict[str, Any]:
    """Start group collaboration task in background."""
    try:
        from app.core.group_collaboration import group_collaboration_engine
        asyncio.create_task(group_collaboration_engine.run_task(task_id))
    except Exception as e:
        logger.error("failed_to_start_task", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start task: {e}")
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
        task.paused_at = datetime.now(timezone.utc)
        await db.commit()
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
        task.completed_at = datetime.now(timezone.utc)
        await db.commit()
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
        task.completed_at = datetime.now(timezone.utc)
        await db.commit()
        return {"ok": True, "task_id": task_id, "status": "cancelled"}


# ─── Scheduler ──────────────────────────────────────────────────────────────

from app.storage.models_platform import Workflow

_SCHEDULER_MARKET = [
    {"name": "daily-summary", "cron": "0 9 * * *", "description": "Daily summary at 9am"},
    {"name": "hourly-check", "cron": "0 * * * *", "description": "Hourly health check"},
]


@router.get("/scheduler")
@router.get("/scheduler/")
async def list_scheduled() -> list[dict[str, Any]]:
    async with async_session() as db:
        rows = (await db.execute(select(Workflow).where(Workflow.schedule != None))).scalars().all()
        return [
            {
                "id": w.id,
                "name": w.name,
                "schedule": w.schedule,
                "last_status": w.last_status,
                "run_count": w.run_count,
            }
            for w in rows
        ]


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


# ─── MCP ────────────────────────────────────────────────────────────────────

from app.storage.models_plugins import MCPServerRecord


def _mcp_dict(m: MCPServerRecord) -> dict[str, Any]:
    return {
        "id": m.id,
        "plugin_id": m.plugin_id,
        "name": m.name,
        "command": m.command,
        "url": m.url,
        "args": m.args,
        "env": m.env,
        "status": m.status,
        "tools_count": m.tools_count,
        "created_at": m.created_at.isoformat() if m.created_at else "",
    }


@router.get("/mcp")
@router.get("/mcp/")
async def list_mcp_servers() -> list[dict[str, Any]]:
    async with async_session() as db:
        rows = (await db.execute(select(MCPServerRecord).order_by(MCPServerRecord.created_at.desc()))).scalars().all()
        return [_mcp_dict(m) for m in rows]


@router.post("/mcp")
@router.post("/mcp/")
async def create_mcp_server(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    async with async_session() as db:
        server = MCPServerRecord(
            plugin_id=data.get("plugin_id"),
            name=data.get("name", "MCP Server"),
            command=data.get("command"),
            url=data.get("url"),
            args=data.get("args", []),
            env=data.get("env", {}),
        )
        db.add(server)
        await db.commit()
        await db.refresh(server)
        return _mcp_dict(server)


@router.post("/mcp/{server_id}/start")
async def start_mcp_server(server_id: str) -> dict[str, Any]:
    async with async_session() as db:
        server = (await db.execute(select(MCPServerRecord).where(MCPServerRecord.id == server_id))).scalars().first()
        if server is None:
            raise HTTPException(status_code=404, detail="MCP server not found")
        server.status = "connected"
        await db.commit()
        return _mcp_dict(server)


@router.post("/mcp/{server_id}/stop")
async def stop_mcp_server(server_id: str) -> dict[str, Any]:
    async with async_session() as db:
        server = (await db.execute(select(MCPServerRecord).where(MCPServerRecord.id == server_id))).scalars().first()
        if server is None:
            raise HTTPException(status_code=404, detail="MCP server not found")
        server.status = "stopped"
        await db.commit()
        return _mcp_dict(server)


@router.delete("/mcp/{server_id}")
async def delete_mcp_server(server_id: str) -> dict[str, Any]:
    async with async_session() as db:
        server = (await db.execute(select(MCPServerRecord).where(MCPServerRecord.id == server_id))).scalars().first()
        if server is None:
            raise HTTPException(status_code=404, detail="MCP server not found")
        await db.delete(server)
        await db.commit()
        return {"ok": True, "deleted": server_id}


# ─── Eval ───────────────────────────────────────────────────────────────────

from app.storage.models_eval import EvalDataset, EvalRun


def _eval_dataset_dict(e: EvalDataset) -> dict[str, Any]:
    return {
        "id": e.id,
        "name": e.name,
        "description": e.description,
        "case_count": e.case_count,
        "created_at": e.created_at.isoformat() if e.created_at else "",
    }


def _eval_run_dict(r: EvalRun) -> dict[str, Any]:
    return {
        "id": r.id,
        "dataset_id": r.dataset_id,
        "agent_id": r.agent_id,
        "total_cases": r.total_cases,
        "passed_cases": r.passed_cases,
        "failed_cases": r.failed_cases,
        "pass_rate": r.pass_rate,
        "average_score": r.average_score,
        "created_at": r.created_at.isoformat() if r.created_at else "",
    }


@router.get("/eval/datasets")
@router.get("/eval/datasets/")
async def list_eval_datasets() -> list[dict[str, Any]]:
    async with async_session() as db:
        rows = (await db.execute(select(EvalDataset).order_by(EvalDataset.created_at.desc()))).scalars().all()
        return [_eval_dataset_dict(e) for e in rows]


@router.post("/eval/datasets")
@router.post("/eval/datasets/")
async def create_eval_dataset(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    async with async_session() as db:
        ds = EvalDataset(
            user_id=DEFAULT_USER,
            name=data.get("name", "New Dataset"),
            description=data.get("description", ""),
            data_json=data.get("data_json", "[]"),
        )
        db.add(ds)
        await db.commit()
        await db.refresh(ds)
        return _eval_dataset_dict(ds)


@router.post("/eval/run")
@router.post("/eval/run/")
async def run_evaluation(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    async with async_session() as db:
        run = EvalRun(
            user_id=DEFAULT_USER,
            dataset_id=data.get("dataset_id", ""),
            agent_id=data.get("agent_id", ""),
            total_cases=int(data.get("total_cases") or 0),
            passed_cases=int(data.get("passed_cases") or 0),
            failed_cases=int(data.get("failed_cases") or 0),
            average_score=float(data.get("average_score") or 0.0),
            pass_rate=float(data.get("pass_rate") or 0.0),
            results_json=data.get("results_json", "[]"),
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)
        return _eval_run_dict(run)


_BUILTIN_EVAL_DATASETS = [
    {
        "name": "general-knowledge",
        "description": "General knowledge Q&A benchmark with factual questions.",
        "cases": [
            {"question": "What is the capital of France?", "expected": "Paris"},
            {"question": "How many planets are in our solar system?", "expected": "8"},
            {"question": "Who wrote Romeo and Juliet?", "expected": "Shakespeare"},
            {"question": "What is the chemical symbol for water?", "expected": "H2O"},
            {"question": "Which ocean is the largest?", "expected": "Pacific"},
        ],
    },
    {
        "name": "reasoning",
        "description": "Logical reasoning and multi-step problem solving benchmark.",
        "cases": [
            {"question": "If all A are B and all B are C, then are all A also C?", "expected": "yes"},
            {"question": "A train leaves at 10:30 and arrives at 14:45. How long is the journey?", "expected": "4 hours 15 minutes"},
            {"question": "Three consecutive integers sum to 24. What is the smallest?", "expected": "7"},
        ],
    },
    {
        "name": "tool-usage",
        "description": "Benchmark for correct tool selection and invocation.",
        "cases": [
            {"question": "Find the current time on the server.", "expected": "tool:get_current_time"},
            {"question": "Search the web for the latest news about AI.", "expected": "tool:web_search"},
            {"question": "Calculate 42 * 17 using a calculator.", "expected": "tool:calculator"},
        ],
    },
]


@router.post("/eval/datasets/seed-builtin")
@router.post("/eval/datasets/seed-builtin/")
async def seed_builtin_eval_datasets() -> dict[str, Any]:
    """Seed the built-in evaluation datasets (idempotent by name)."""
    async with async_session() as db:
        existing_names = set(
            (await db.execute(select(EvalDataset.name))).scalars().all()
        )
        added: list[EvalDataset] = []
        for spec in _BUILTIN_EVAL_DATASETS:
            if spec["name"] in existing_names:
                continue
            ds = EvalDataset(
                user_id=DEFAULT_USER,
                name=spec["name"],
                description=spec["description"],
                data_json=json.dumps(spec["cases"], ensure_ascii=False),
                case_count=len(spec["cases"]),
            )
            db.add(ds)
            added.append(ds)
        await db.commit()
        for ds in added:
            await db.refresh(ds)
        return {"ok": True, "created": len(added), "datasets": [_eval_dataset_dict(ds) for ds in added]}


@router.post("/eval/datasets/{dataset_id}/run")
@router.post("/eval/datasets/{dataset_id}/run/")
async def run_eval_dataset(dataset_id: str) -> dict[str, Any]:
    """Run an evaluation against an existing dataset (reuses /eval/run logic)."""
    from app.storage.database import Agent

    async with async_session() as db:
        ds = (await db.execute(select(EvalDataset).where(EvalDataset.id == dataset_id))).scalar_one_or_none()
        if not ds:
            raise HTTPException(status_code=404, detail="Dataset not found")
        agent = (await db.execute(
            select(Agent).where(Agent.user_id == DEFAULT_USER).order_by(Agent.created_at.asc())
        )).scalars().first()
        if not agent:
            agent = (await db.execute(select(Agent).order_by(Agent.created_at.asc()))).scalars().first()
        if not agent:
            raise HTTPException(status_code=400, detail="No agent available to run evaluation")
        run = EvalRun(
            user_id=DEFAULT_USER,
            dataset_id=dataset_id,
            agent_id=agent.id,
            total_cases=ds.case_count,
            passed_cases=0,
            failed_cases=0,
            average_score=0.0,
            pass_rate=0.0,
            results_json="[]",
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)
        return _eval_run_dict(run)


# ─── Cost ───────────────────────────────────────────────────────────────────

from app.storage.models_cost import CostRecord, BudgetConfig, UsageQuota


def _cost_dict(c: CostRecord) -> dict[str, Any]:
    return {
        "id": c.id,
        "provider": c.provider,
        "model_id": c.model_id,
        "prompt_tokens": c.prompt_tokens,
        "completion_tokens": c.completion_tokens,
        "total_tokens": c.total_tokens,
        "input_cost": c.input_cost,
        "output_cost": c.output_cost,
        "total_cost": c.total_cost,
        "created_at": c.created_at.isoformat() if c.created_at else "",
    }


@router.get("/cost/records")
@router.get("/cost/records/")
async def list_cost_records(session_id: str = "") -> list[dict[str, Any]]:
    async with async_session() as db:
        stmt = select(CostRecord).order_by(CostRecord.created_at.desc())
        if session_id:
            stmt = stmt.where(CostRecord.session_id == session_id)
        rows = (await db.execute(stmt)).scalars().all()
        return [_cost_dict(c) for c in rows]


@router.get("/cost/budget")
@router.get("/cost/budget/")
async def get_budget() -> dict[str, Any]:
    async with async_session() as db:
        cfg = (await db.execute(select(BudgetConfig).where(BudgetConfig.user_id == DEFAULT_USER))).scalars().first()
        if cfg is None:
            cfg = BudgetConfig(user_id=DEFAULT_USER)
            db.add(cfg)
            await db.commit()
            await db.refresh(cfg)
        return {
            "amount": cfg.amount,
            "period": cfg.period,
            "is_active": cfg.is_active,
            "per_session_limit": cfg.per_session_limit,
            "per_request_limit": cfg.per_request_limit,
        }


@router.get("/cost/quota")
@router.get("/cost/quota/")
async def get_quota() -> dict[str, Any]:
    async with async_session() as db:
        q = (await db.execute(select(UsageQuota).where(UsageQuota.user_id == DEFAULT_USER))).scalars().first()
        if q is None:
            q = UsageQuota(user_id=DEFAULT_USER)
            db.add(q)
            await db.commit()
            await db.refresh(q)
        return {
            "max_requests_per_day": q.max_requests_per_day,
            "max_tokens_per_day": q.max_tokens_per_day,
            "max_cost_per_month": q.max_cost_per_month,
            "requests_today": q.requests_today,
            "tokens_today": q.tokens_today,
            "cost_this_month": q.cost_this_month,
        }


# ─── Search ─────────────────────────────────────────────────────────────────

from app.storage.models_platform import DocumentChunk


@router.get("/search")
@router.get("/search/")
async def search_documents(q: str = "", limit: int = 20) -> list[dict[str, Any]]:
    if not q:
        return []
    async with async_session() as db:
        pattern = f"%{q}%"
        rows = (
            await db.execute(
                select(DocumentChunk)
                .where(DocumentChunk.content.ilike(pattern))
                .order_by(DocumentChunk.created_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        return [
            {
                "id": c.id,
                "document_id": c.document_id,
                "content": c.content,
                "chunk_index": c.chunk_index,
                "score": 0.0,
                "created_at": c.created_at.isoformat() if c.created_at else "",
            }
            for c in rows
        ]


# ─── WebSocket ──────────────────────────────────────────────────────────────

@router.websocket("/ws/{session_id}")
async def ws_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    await websocket.send_json({"type": "connected", "session_id": session_id})
    try:
        while True:
            msg = await websocket.receive_text()
            await websocket.send_json({"type": "echo", "data": msg})
    except Exception as e:
        logger.warning("generic.ws_endpoint_disconnect", error=str(e))
    finally:
        try:
            await websocket.close()
        except Exception as e:
            logger.warning("generic.ws_endpoint_close", error=str(e))


@router.websocket("/ws/groups/{group_id}")
async def ws_group_endpoint(websocket: WebSocket, group_id: str):
    from app.core.group_ws_hub import group_ws_hub

    # Accept connection first to read query params
    await websocket.accept()

    # Read token from query params (optional for now, required in future)
    token = websocket.query_params.get("token", "")
    user_id = websocket.query_params.get("user_id", "guest")

    # Validate group exists
    async with async_session() as db:
        group = (await db.execute(select(AgentGroup).where(AgentGroup.id == group_id))).scalar_one_or_none()
        if group is None:
            await websocket.send_json({"type": "error", "error": "group_not_found"})
            await websocket.close()
            return

    await group_ws_hub.connect(group_id, websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "error": "invalid_json"})
                continue

            # Inject user info into message
            if payload.get("type") == "message":
                payload.setdefault("sender_id", user_id)

            result = await group_ws_hub.handle_message(group_id, payload)
            await websocket.send_json({"type": "ack", "data": result})
    except Exception as e:
        logger.warning("generic.ws_group_endpoint_disconnect", error=str(e))
    finally:
        await group_ws_hub.disconnect(group_id, websocket)
        try:
            await websocket.close()
        except Exception as e:
            logger.warning("generic.ws_group_endpoint_close", error=str(e))

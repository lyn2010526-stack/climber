"""Miscellaneous API endpoints for various resources."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.v1.common import DEFAULT_USER, current_user_id, get_or_404, ok_response, parse_request_payload
from app.storage import async_session
from app.storage.database import Document
from app.storage.models_platform import Cluster, DocumentChunk, Trace, Workflow
from app.storage.models_plugins import MCPServerRecord, PluginRecord

logger = structlog.get_logger(__name__)

router = APIRouter()


# ─── Models ─────────────────────────────────────────────────────────────────


@router.get("/models")
@router.get("/models/")
async def list_models() -> list[dict[str, Any]]:
    """Return known models per provider, plus locally discovered Ollama models."""
    from app.models.registry import MODEL_ALIASES

    model_registry = __import__("app.core.di", fromlist=["resolve"]).resolve("ModelRegistry")
    models: list[dict[str, Any]] = []
    seen: set[str] = set()

    for alias, (provider, model_id) in MODEL_ALIASES.items():
        key = f"{provider}:{model_id}"
        if key not in seen:
            seen.add(key)
            models.append({"provider": provider, "model_id": model_id, "label": alias})

    for m in model_registry.list_models():
        key = f"{m['provider']}:{m['model_id']}"
        if key not in seen:
            seen.add(key)
            models.append({"provider": m["provider"], "model_id": m["model_id"], "label": m["model_id"]})

    await _add_local_ollama_models(models)
    return models


async def _add_local_ollama_models(models: list[dict[str, Any]]) -> None:
    """Discover and append local Ollama models if daemon is reachable.

    Args:
        models: The model list to append to.
    """
    try:
        import httpx

        from app.config import settings

        base = getattr(settings, "ollama_base_url", "http://localhost:11434")
        async with httpx.AsyncClient(timeout=1.5) as client:
            resp = await client.get(f"{base}/api/tags")
            if resp.status_code == 200:
                for m in resp.json().get("models", []):
                    models.append(
                        {"provider": "ollama", "model_id": m.get("name", ""), "label": f"{m.get('name', '')} (local)"}
                    )
    except Exception as e:
        logger.warning("list_models_ollama_discovery", error=str(e))


# ─── Tools ──────────────────────────────────────────────────────────────────


@router.get("/tools")
@router.get("/tools/")
async def list_tools() -> list[dict[str, Any]]:
    """List all registered tools from the tool registry."""
    import app.tools.builtins  # noqa: F401  ensures builtin tools are registered
    tool_registry = __import__("app.core.di", fromlist=["resolve"]).resolve("ToolRegistry")

    return [
        {"name": t.name, "description": t.description, "parameters": t.parameters}
        for t in tool_registry.list_tools()
    ]


# ─── Stats ──────────────────────────────────────────────────────────────────


@router.get("/stats")
@router.get("/stats/")
async def get_stats() -> dict[str, Any]:
    """Get system-wide statistics."""
    from app.storage.database import Agent, ApiKey, Message, Session, UsageLog

    async with async_session() as db:
        async def count(model: Any) -> int:
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
            "total_crews": await count(__import__("app.storage.models_platform", fromlist=["Crew"]).Crew),
        }


# ─── Profile ───────────────────────────────────────────────────────────────


@router.get("/profile")
@router.get("/profile/")
async def get_profile() -> dict[str, Any]:
    """Get the current user profile."""
    return {"id": DEFAULT_USER, "display_name": "Local User", "email": "local@localhost", "is_admin": True}


# ─── Cluster ────────────────────────────────────────────────────────────────


@router.get("/cluster")
@router.get("/cluster/")
async def list_cluster_nodes() -> list[dict[str, Any]]:
    """List all cluster nodes."""
    async with async_session() as db:
        rows = (await db.execute(select(Cluster).order_by(Cluster.created_at.desc()))).scalars().all()
        return [_cluster_node_dict(n) for n in rows]


@router.post("/cluster")
@router.post("/cluster/")
@router.post("/cluster/create")
async def create_cluster_node(request: Request) -> dict[str, Any]:
    """Create a new cluster node."""
    data = await parse_request_payload(request)
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
    """Get cluster status summary."""
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
    """Get detailed cluster statistics."""
    async with async_session() as db:
        rows = (await db.execute(select(Cluster))).scalars().all()
        total = len(rows)
        online = sum(1 for n in rows if n.status == "online")
        roles: dict[str, int] = {}
        for n in rows:
            roles[n.role] = roles.get(n.role, 0) + 1
        return {"total": total, "online": online, "offline": total - online, "roles": roles}


@router.delete("/cluster/{node_id}")
async def delete_cluster_node(node_id: str) -> dict[str, bool | str]:
    """Delete a cluster node."""
    async with async_session() as db:
        node = await get_or_404(db, Cluster, node_id, detail="Node not found")
        await db.delete(node)
        await db.commit()
        return ok_response(node_id)


# ─── Traces ─────────────────────────────────────────────────────────────────


@router.get("/traces")
@router.get("/traces/")
async def list_traces(request: Request, limit: int = 100) -> list[dict[str, Any]]:
    """List the current user's traces ordered by creation date (newest first)."""
    user_id = current_user_id(request)
    async with async_session() as db:
        rows = (
            await db.execute(
                select(Trace)
                .where(Trace.user_id == user_id)
                .order_by(Trace.created_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        return [_trace_dict(t) for t in rows]


@router.get("/traces/{trace_id}")
async def get_trace(trace_id: str, request: Request) -> dict[str, Any]:
    """Get a single trace by ID."""
    user_id = current_user_id(request)
    async with async_session() as db:
        t = (
            await db.execute(select(Trace).where(Trace.id == trace_id, Trace.user_id == user_id))
        ).scalar_one_or_none()
        if t is None:
            raise HTTPException(status_code=404, detail="Trace not found")
        return _trace_detail_dict(t)


# ─── Plugins ────────────────────────────────────────────────────────────────


@router.get("/plugins")
@router.get("/plugins/")
async def list_plugins(type: str = "") -> list[dict[str, Any]]:
    """List installed plugins, optionally filtered by category."""
    async with async_session() as db:
        stmt = select(PluginRecord).order_by(PluginRecord.installed_at.desc())
        if type:
            stmt = stmt.where(PluginRecord.category == type)
        rows = (await db.execute(stmt)).scalars().all()
        return [_plugin_dict(p) for p in rows]


@router.get("/plugins/marketplace")
@router.get("/plugins/marketplace/")
async def get_marketplace() -> list[dict[str, Any]]:
    """Get plugin marketplace catalog with installation status."""
    from app.config import settings

    installed = set()
    async with async_session() as db:
        installed = {
            p.plugin_key
            for p in (await db.execute(select(PluginRecord))).scalars().all()
            if p.plugin_key
        }
    return [{**item, "is_installed": item["plugin_key"] in installed} for item in settings.plugin_marketplace]


@router.get("/plugins/categories")
@router.get("/plugins/categories/")
async def get_plugin_categories() -> list[str]:
    """Get all plugin categories (both installed and marketplace)."""
    from app.config import settings

    async with async_session() as db:
        rows = (await db.execute(select(PluginRecord.category).distinct())).scalars().all()
    return sorted({*(r for r in (rows or []) if r), *(m["category"] for m in settings.plugin_marketplace)})


@router.post("/plugins/{plugin_key}/install")
async def install_plugin(plugin_key: str, request: Request) -> dict[str, Any]:
    """Install a plugin from the marketplace or with custom data."""
    from app.config import settings

    entry = next((m for m in settings.plugin_marketplace if m["plugin_key"] == plugin_key), None)
    data = await parse_request_payload(request)
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


@router.post("/plugins/{plugin_id}/enable")
async def enable_plugin(plugin_id: str) -> dict[str, Any]:
    """Enable a plugin by ID or key."""
    return await _set_plugin_enabled(plugin_id, True)


@router.post("/plugins/{plugin_id}/disable")
async def disable_plugin(plugin_id: str) -> dict[str, Any]:
    """Disable a plugin by ID or key."""
    return await _set_plugin_enabled(plugin_id, False)


@router.delete("/plugins/{plugin_id}")
@router.post("/plugins/{plugin_id}/uninstall")
async def uninstall_plugin(plugin_id: str) -> dict[str, bool | str]:
    """Uninstall a plugin by ID or key."""
    async with async_session() as db:
        plugin = await _find_plugin(db, plugin_id)
        if plugin is None:
            raise HTTPException(status_code=404, detail="Plugin not found")
        await db.delete(plugin)
        await db.commit()
        return ok_response(plugin_id)


@router.get("/plugins/{plugin_id}/status")
async def get_plugin_status(plugin_id: str) -> dict[str, Any]:
    """Get plugin installation status."""
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
    """Import a custom plugin."""
    data = await parse_request_payload(request)
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


# ─── Scheduler ──────────────────────────────────────────────────────────────


@router.get("/scheduler")
@router.get("/scheduler/")
async def list_scheduled() -> list[dict[str, Any]]:
    """List all scheduled workflows."""
    async with async_session() as db:
        rows = (await db.execute(select(Workflow).where(Workflow.schedule is not None))).scalars().all()
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
    """Create a scheduled workflow."""
    data = await parse_request_payload(request)
    user_id = current_user_id(request)
    async with async_session() as db:
        wf = Workflow(
            user_id=user_id,
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


@router.get("/mcp")
@router.get("/mcp/")
async def list_mcp_servers() -> list[dict[str, Any]]:
    """List all MCP servers."""
    async with async_session() as db:
        rows = (await db.execute(select(MCPServerRecord).order_by(MCPServerRecord.created_at.desc()))).scalars().all()
        return [_mcp_dict(m) for m in rows]


@router.post("/mcp")
@router.post("/mcp/")
async def create_mcp_server(request: Request) -> dict[str, Any]:
    """Create a new MCP server."""
    data = await parse_request_payload(request)
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
    """Start an MCP server."""
    async with async_session() as db:
        server = await get_or_404(db, MCPServerRecord, server_id, detail="MCP server not found")
        server.status = "connected"
        await db.commit()
        return _mcp_dict(server)


@router.post("/mcp/{server_id}/stop")
async def stop_mcp_server(server_id: str) -> dict[str, Any]:
    """Stop an MCP server."""
    async with async_session() as db:
        server = await get_or_404(db, MCPServerRecord, server_id, detail="MCP server not found")
        server.status = "stopped"
        await db.commit()
        return _mcp_dict(server)


@router.delete("/mcp/{server_id}")
async def delete_mcp_server(server_id: str) -> dict[str, bool | str]:
    """Delete an MCP server."""
    async with async_session() as db:
        server = await get_or_404(db, MCPServerRecord, server_id, detail="MCP server not found")
        await db.delete(server)
        await db.commit()
        return ok_response(server_id)


# ─── Eval ───────────────────────────────────────────────────────────────────


@router.get("/eval/datasets")
@router.get("/eval/datasets/")
async def list_eval_datasets(request: Request) -> list[dict[str, Any]]:
    """List evaluation datasets."""
    from app.storage.models_eval import EvalDataset

    user_id = current_user_id(request)
    async with async_session() as db:
        rows = (
            await db.execute(
                select(EvalDataset)
                .where(EvalDataset.user_id == user_id)
                .order_by(EvalDataset.created_at.desc())
            )
        ).scalars().all()
        return [_eval_dataset_dict(e) for e in rows]


@router.post("/eval/datasets")
@router.post("/eval/datasets/")
async def create_eval_dataset(request: Request) -> dict[str, Any]:
    """Create an evaluation dataset."""
    from app.storage.models_eval import EvalDataset

    data = await parse_request_payload(request)
    user_id = current_user_id(request)
    async with async_session() as db:
        ds = EvalDataset(
            user_id=user_id,
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
    """Create an evaluation run record."""
    from app.storage.database import Agent
    from app.storage.models_eval import EvalDataset, EvalRun

    data = await parse_request_payload(request)
    user_id = current_user_id(request)
    dataset_id = str(data.get("dataset_id") or "").strip()
    agent_id = str(data.get("agent_id") or "").strip()
    if not dataset_id:
        raise HTTPException(status_code=422, detail="dataset_id is required")
    if not agent_id:
        raise HTTPException(status_code=422, detail="agent_id is required")
    async with async_session() as db:
        dataset = await db.get(EvalDataset, dataset_id)
        if dataset is None or dataset.user_id != user_id:
            raise HTTPException(status_code=404, detail="Evaluation dataset not found")
        agent = await db.get(Agent, agent_id)
        if agent is None or agent.user_id != user_id:
            raise HTTPException(status_code=404, detail="Agent not found")
        run = EvalRun(
            user_id=user_id,
            dataset_id=dataset_id,
            agent_id=agent_id,
            total_cases=int(data.get("total_cases") or 0),
            passed_cases=int(data.get("passed_cases") or 0),
            failed_cases=int(data.get("failed_cases") or 0),
            average_score=float(data.get("average_score") or 0.0),
            pass_rate=float(data.get("pass_rate") or 0.0),
            results_json=data.get("results_json", "[]"),
        )
        db.add(run)
        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise HTTPException(status_code=409, detail="Evaluation run conflicts with stored data") from exc
        await db.refresh(run)
        return _eval_run_dict(run)


# ─── Cost ───────────────────────────────────────────────────────────────────


@router.get("/cost/records")
@router.get("/cost/records/")
async def list_cost_records(request: Request, session_id: str = "") -> list[dict[str, Any]]:
    """List the current user's cost records, optionally filtered by session ID."""
    from app.storage.models_cost import CostRecord

    user_id = current_user_id(request)
    async with async_session() as db:
        stmt = (
            select(CostRecord)
            .where(CostRecord.user_id == user_id)
            .order_by(CostRecord.created_at.desc())
        )
        if session_id:
            stmt = stmt.where(CostRecord.session_id == session_id)
        rows = (await db.execute(stmt)).scalars().all()
        return [_cost_dict(c) for c in rows]


@router.get("/cost/budget")
@router.get("/cost/budget/")
async def get_budget(request: Request) -> dict[str, Any]:
    """Get or create budget configuration for the current user."""
    from app.storage.models_cost import BudgetConfig

    user_id = current_user_id(request)
    async with async_session() as db:
        cfg = (await db.execute(select(BudgetConfig).where(BudgetConfig.user_id == user_id))).scalars().first()
        if cfg is None:
            cfg = BudgetConfig(user_id=user_id)
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
async def get_quota(request: Request) -> dict[str, Any]:
    """Get or create usage quota for the current user."""
    from app.storage.models_cost import UsageQuota

    user_id = current_user_id(request)
    async with async_session() as db:
        q = (await db.execute(select(UsageQuota).where(UsageQuota.user_id == user_id))).scalars().first()
        if q is None:
            q = UsageQuota(user_id=user_id)
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


@router.get("/search")
@router.get("/search/")
async def search_documents(request: Request, q: str = "", limit: int = 20) -> list[dict[str, Any]]:
    """Search the current user's document chunks by content (case-insensitive LIKE)."""
    if not q:
        return []
    user_id = current_user_id(request)
    async with async_session() as db:
        pattern = f"%{q}%"
        rows = (
            await db.execute(
                select(DocumentChunk)
                .join(Document, Document.id == DocumentChunk.document_id)
                .where(
                    DocumentChunk.content.ilike(pattern),
                    Document.user_id == user_id,
                )
                .order_by(DocumentChunk.created_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        return [_chunk_dict(c) for c in rows]


# ─── Helper Functions ────────────────────────────────────────────────────────


async def _find_plugin(db: Any, plugin_id: str) -> PluginRecord | None:
    """Find a plugin by ID or plugin_key.

    Args:
        db: The async database session.
        plugin_id: The plugin ID or key to search for.

    Returns:
        The PluginRecord if found, None otherwise.
    """
    return (
        await db.execute(
            select(PluginRecord).where(
                (PluginRecord.id == plugin_id) | (PluginRecord.plugin_key == plugin_id)
            )
        )
    ).scalars().first()


async def _set_plugin_enabled(plugin_id: str, enabled: bool) -> dict[str, Any]:
    """Set a plugin's enabled status.

    Args:
        plugin_id: The plugin ID or key.
        enabled: True to enable, False to disable.

    Returns:
        A dictionary with the updated status.
    """
    async with async_session() as db:
        plugin = await _find_plugin(db, plugin_id)
        if plugin is None:
            raise HTTPException(status_code=404, detail="Plugin not found")
        plugin.status = "enabled" if enabled else "disabled"
        await db.commit()
        return {"ok": True, "id": plugin.id, "is_enabled": enabled, "status": plugin.status}


def _cluster_node_dict(n: Cluster) -> dict[str, Any]:
    """Convert a Cluster model instance to a response dictionary."""
    return {
        "id": n.id,
        "name": n.name,
        "endpoint": n.endpoint,
        "role": n.role,
        "status": n.status,
        "capabilities": n.capabilities or [],
        "last_heartbeat": n.last_heartbeat.isoformat() if n.last_heartbeat else None,
    }


def _trace_dict(t: Trace) -> dict[str, Any]:
    """Convert a Trace model instance to a summary response dictionary."""
    return {
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


def _trace_detail_dict(t: Trace) -> dict[str, Any]:
    """Convert a Trace model instance to a detailed response dictionary."""
    base = _trace_dict(t)
    base.update({
        "input_data": t.input_data,
        "output_data": t.output_data,
    })
    return base


def _plugin_dict(p: PluginRecord) -> dict[str, Any]:
    """Convert a PluginRecord model instance to a response dictionary."""
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


def _mcp_dict(m: MCPServerRecord) -> dict[str, Any]:
    """Convert an MCPServerRecord model instance to a response dictionary."""
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


def _eval_dataset_dict(e: Any) -> dict[str, Any]:
    """Convert an EvalDataset model instance to a response dictionary."""
    return {
        "id": e.id,
        "name": e.name,
        "description": e.description,
        "case_count": e.case_count,
        "created_at": e.created_at.isoformat() if e.created_at else "",
    }


def _eval_run_dict(r: Any) -> dict[str, Any]:
    """Convert an EvalRun model instance to a response dictionary."""
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


def _cost_dict(c: Any) -> dict[str, Any]:
    """Convert a CostRecord model instance to a response dictionary."""
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


def _chunk_dict(c: DocumentChunk) -> dict[str, Any]:
    """Convert a DocumentChunk model instance to a response dictionary."""
    return {
        "id": c.id,
        "document_id": c.document_id,
        "content": c.content,
        "chunk_index": c.chunk_index,
        "score": 0.0,
        "created_at": c.created_at.isoformat() if c.created_at else "",
    }

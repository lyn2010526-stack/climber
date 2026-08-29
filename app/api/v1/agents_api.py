"""Agent, tool, model and cache-metrics endpoints.

Split out of the former monolithic generic API module (pure move refactor).
Routes are registered with and without a trailing slash because the app runs
with redirect_slashes=False.
"""

from __future__ import annotations

import time
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select

from app.api.v1._shared import (
    DEFAULT_USER,
    _agent_detail_cache,
    _agents_cache,
    _agents_created_total,
    _agents_deleted_total,
    _cache_hits_total,
    _cache_misses_total,
    _cache_ttl_seconds,
    _db_queries_total,
    _db_query_duration_seconds,
    _hybrid_agent_detail,
    _hybrid_agents,
    _hybrid_models,
    _models_cache,
    _payload,
)
from app.core.api_key_crypto import encrypt_api_key
from app.core.auth import get_current_user
from app.core.di import resolve as di_resolve
from app.storage import async_session

router = APIRouter(dependencies=[Depends(get_current_user)])
logger = structlog.get_logger()

# ─── Agents ─────────────────────────────────────────────────────────────────

@router.get("/agents")
@router.get("/agents/")
async def list_agents(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    use_cache = limit == 100 and offset == 0
    # Check hybrid cache (Redis or local)
    if use_cache:
        hybrid = await _hybrid_agents.get_scalar()
        if hybrid is not None:
            _cache_hits_total.labels(cache_type='agents').inc()
            return hybrid[:limit]

    # Fallback: check legacy local cache
    if use_cache:
        cached = _agents_cache.get()
        if cached is not None:
            _cache_hits_total.labels(cache_type='agents').inc()
            return cached[:limit]

    _cache_misses_total.labels(cache_type='agents').inc()

    from app.storage.database import Agent

    start = time.monotonic()
    async with async_session() as db:
        rows = (
            await db.execute(
                select(Agent)
                .order_by(Agent.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        ).scalars().all()
        result = [
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
    if use_cache:
        _agents_cache.set(result)
        await _hybrid_agents.set_scalar(result)

    _db_query_duration_seconds.labels(endpoint='agents', operation='list').observe(time.monotonic() - start)
    _db_queries_total.labels(endpoint='agents', operation='list').inc()
    return result


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
        _agents_cache.set(None)  # invalidate local
        await _hybrid_agents.invalidate_scalar()
        _agents_created_total.inc()
        return {
            "id": agent.id,
            "name": agent.name,
            "provider": agent.provider,
            "model_id": agent.model_id,
            "base_url": agent.base_url,
        }


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str) -> dict[str, Any]:
    # Check hybrid cache (Redis or local)
    hybrid = await _hybrid_agent_detail.get_keyed(agent_id)
    if hybrid is not None:
        return hybrid

    # Fallback: check legacy local cache
    cached = _agent_detail_cache.get(agent_id)
    if cached is not None:
        return cached

    from app.storage.database import Agent

    async with async_session() as db:
        agent = (await db.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        result = {
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
    _agent_detail_cache.set(agent_id, result)
    await _hybrid_agent_detail.set_keyed(agent_id, result)
    return result


@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str) -> dict:
    from sqlalchemy import delete

    from app.storage.database import Agent, Turn, UsageLog
    from app.storage.database import Message as MessageModel
    from app.storage.database import Session as SessionModel
    from app.storage.models_cost import CostRecord
    from app.storage.models_feedback import Feedback

    async with async_session() as db:
        agent = (await db.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        session_ids = (await db.execute(
            select(SessionModel.id).where(SessionModel.agent_id == agent_id)
        )).scalars().all()
        if session_ids:
            message_ids = (await db.execute(
                select(MessageModel.id).where(MessageModel.session_id.in_(session_ids))
            )).scalars().all()
            if message_ids:
                await db.execute(delete(Feedback).where(Feedback.message_id.in_(message_ids)))
            await db.execute(delete(MessageModel).where(MessageModel.session_id.in_(session_ids)))
            await db.execute(delete(Turn).where(Turn.session_id.in_(session_ids)))
            await db.execute(delete(UsageLog).where(UsageLog.session_id.in_(session_ids)))
            await db.execute(delete(CostRecord).where(CostRecord.session_id.in_(session_ids)))
            await db.execute(delete(SessionModel).where(SessionModel.agent_id == agent_id))
        from app.storage.models_eval import EvalRun
        from app.storage.models_memory import CoreMemoryBlock, EpisodicMemory
        await db.execute(delete(EvalRun).where(EvalRun.agent_id == agent_id))
        await db.execute(delete(EpisodicMemory).where(EpisodicMemory.agent_id == agent_id))
        await db.execute(delete(CoreMemoryBlock).where(CoreMemoryBlock.agent_id == agent_id))
        await db.execute(delete(Agent).where(Agent.id == agent_id))
        await db.commit()
        _agents_cache.set(None)  # invalidate local
        _agent_detail_cache.invalidate(agent_id)
        await _hybrid_agents.invalidate_scalar()
        await _hybrid_agent_detail.invalidate_keyed(agent_id)
        _agents_deleted_total.inc()
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
    # Check hybrid cache (Redis or local)
    hybrid = await _hybrid_models.get_scalar()
    if hybrid is not None:
        _cache_hits_total.labels(cache_type='models').inc()
        return hybrid

    # Fallback: check legacy local cache
    cached = _models_cache.get()
    if cached is not None:
        _cache_hits_total.labels(cache_type='models').inc()
        return cached

    _cache_misses_total.labels(cache_type='models').inc()

    """Return known models per provider, plus locally discovered Ollama models."""
    from app.models.registry import MODEL_ALIASES

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

    # Discover local Ollama models when the daemon is reachable (cache the result for 5 min)
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

    _models_cache.set(models)
    await _hybrid_models.set_scalar(models)
    _cache_ttl_seconds.labels(cache_type='models').observe(300.0)
    return models


@router.get("/cache_metrics")
@router.get("/cache_metrics/")
async def cache_metrics() -> dict[str, Any]:
    """Expose cache hit/miss statistics for monitoring."""
    return {
        "agents_cache_ttl": 120.0,
        "models_cache_ttl": 300.0,
        "agent_detail_cache_ttl": 60.0,
    }

"""Integration API endpoints for LangGraph, Mem0, and Pydantic-AI."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.auth_manager import require_admin, require_scopes

logger = structlog.get_logger(__name__)


def _identity() -> tuple[str, bool]:
    from app.config import settings
    from app.core.principal import LOCAL_SUBJECT_ID, get_context_principal

    principal = get_context_principal()
    is_admin = principal.role == "admin" or "admin" in principal.scopes
    if not settings.enable_auth and principal.subject_id == LOCAL_SUBJECT_ID:
        is_admin = True
    return principal.subject_id, is_admin

router = APIRouter()


def _domestic_provider():
    from app.config import settings
    from app.core.integration.domestic_provider import DisabledQQBotProvider, LocalQQBotProvider
    from app.core.security.domestic_adapter import QRTokenStore

    provider = getattr(_domestic_provider, "_provider", None)
    if provider is None or getattr(provider, "_mode", None) != settings.domestic_provider_mode:
        store = QRTokenStore(ttl_seconds=settings.domestic_qr_ttl_seconds)
        provider = (
            LocalQQBotProvider(store)
            if settings.domestic_provider_mode == "local" and settings.domestic_integrations_enabled
            else DisabledQQBotProvider(store)
        )
        provider._mode = settings.domestic_provider_mode
        _domestic_provider._provider = provider
    return provider


def _provider_status_payload(provider: Any) -> dict[str, Any]:
    status = provider.status()
    return {
        "provider": status.provider,
        "enabled": status.enabled,
        "mode": status.mode,
        "reason": status.reason,
    }


@router.get("/integrations/domestic/status")
async def domestic_status() -> dict[str, Any]:
    """Expose an explicit offline/disabled status for domestic adapters."""
    return {"status": "ok", "provider": _provider_status_payload(_domestic_provider())}


@router.post("/integrations/domestic/qqbot/qr")
async def create_domestic_qr(
    _auth: dict = Depends(require_scopes("write")),
) -> dict[str, Any]:
    """Return a clear disabled response without contacting an external platform."""
    provider = _domestic_provider()
    if not provider.status().enabled:
        return {"status": "disabled", "provider": "qqbot", "reason": provider.status().reason}
    token = provider.issue_binding_token()
    return {"status": "ok", "provider": "qqbot", "token": token.token, "expires_at": token.expires_at.isoformat()}


@router.post("/integrations/domestic/qqbot/webhook")
async def domestic_webhook(request: Request) -> dict[str, Any]:
    """Validate webhook bytes without dispatching them to a real QQBot client."""
    from app.config import settings
    from app.core.security.domestic_adapter import verify_webhook_signature

    body = await request.body()
    if not settings.domestic_integrations_enabled:
        return {"status": "disabled", "provider": "qqbot", "reason": "domestic integrations are disabled"}
    valid = verify_webhook_signature(
        settings.domestic_webhook_secret,
        body,
        request.headers.get("x-signature", ""),
        request.headers.get("x-timestamp", ""),
        max_skew_seconds=settings.domestic_webhook_max_skew_seconds,
    )
    if not valid:
        raise HTTPException(status_code=401, detail="invalid webhook signature")
    return {"status": "accepted", "provider": "qqbot", "dispatched": False}


# ─── LangGraph Endpoints ───

@router.get("/integrations/langgraph/graphs")
async def list_langgraph() -> dict[str, Any]:
    """List all registered LangGraph graphs."""
    try:
        from app.core.integration.langgraph_bridge import get_bridge

        bridge = get_bridge()
        return {"graphs": bridge.list_graphs(), "status": "ok"}
    except Exception as exc:
        logger.warning("langgraph_list_failed", error=str(exc))
        return {"graphs": [], "status": "unavailable"}


@router.post("/integrations/langgraph/{graph_name}/invoke")
async def invoke_langgraph(
    graph_name: str,
    payload: dict[str, Any],
    _auth: dict = Depends(require_admin()),
) -> dict[str, Any]:
    """Invoke a LangGraph graph."""
    try:
        from app.core.integration.langgraph_bridge import get_bridge

        bridge = get_bridge()
        inputs = payload.get("inputs", {})
        config = payload.get("config", {})
        result = await bridge.invoke(graph_name, inputs, config)
        return {"result": result, "status": "ok"}
    except ImportError as exc:
        logger.warning("langgraph_runtime_missing", graph=graph_name, error=str(exc))
        raise HTTPException(status_code=424, detail="LangGraph runtime is not installed") from exc
    except ValueError as exc:
        logger.warning("langgraph_invoke_rejected", graph=graph_name, error=str(exc))
        raise HTTPException(status_code=404, detail="LangGraph graph not found") from exc
    except Exception as exc:
        logger.warning("langgraph_invoke_failed", graph=graph_name, error=str(exc))
        raise HTTPException(status_code=500, detail="LangGraph invocation failed") from exc


# ─── Mem0 Endpoints ───

@router.get("/integrations/mem0/status")
async def mem0_status() -> dict[str, Any]:
    """Check Mem0 service availability."""
    try:
        from app.core.integration.mem0_memory import get_mem0_service

        svc = get_mem0_service()
        return {"available": svc.is_available, "status": "ok"}
    except Exception as exc:
        logger.warning("mem0_status_failed", error=str(exc))
        return {"available": False, "status": "unavailable"}


@router.post("/integrations/mem0/search")
async def mem0_search(
    payload: dict[str, Any],
    _auth: dict = Depends(require_scopes("read")),
) -> dict[str, Any]:
    """Search Mem0 memories scoped to the caller."""
    try:
        from app.core.integration.mem0_memory import get_mem0_service

        svc = get_mem0_service()
        query = payload.get("query", "")
        try:
            limit = int(payload.get("limit") or 10)
        except (TypeError, ValueError):
            limit = 10
        limit = max(1, min(limit, 500))
        caller_id, is_admin = _identity()
        # Non-admins can only search their own namespace; admins may pass an explicit user_id.
        requested_user = str(payload.get("user_id") or "").strip()
        user_id = requested_user if (is_admin and requested_user) else caller_id

        if not svc.is_available and not await svc.initialize():
            return {"results": [], "status": "unavailable"}

        results = await svc.search(query, limit=limit, user_id=user_id)
        return {"results": results, "status": "ok"}
    except ImportError as exc:
        logger.warning("mem0_runtime_missing", error=str(exc))
        raise HTTPException(status_code=424, detail="Mem0 runtime is not installed") from exc
    except Exception as exc:
        logger.warning("mem0_search_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Mem0 search failed") from exc


@router.post("/integrations/mem0/add")
async def mem0_add(
    payload: dict[str, Any],
    _auth: dict = Depends(require_scopes("write")),
) -> dict[str, Any]:
    """Add a memory to Mem0 under the caller's namespace."""
    try:
        from app.core.integration.mem0_memory import get_mem0_service

        svc = get_mem0_service()
        content = payload.get("content", "")
        metadata = payload.get("metadata", {})
        caller_id, is_admin = _identity()
        requested_user = str(payload.get("user_id") or "").strip()
        user_id = requested_user if (is_admin and requested_user) else caller_id

        if not svc.is_available and not await svc.initialize():
            raise HTTPException(status_code=503, detail="Mem0 not available")

        memory_id = await svc.add(content, metadata=metadata, user_id=user_id)
        return {"memory_id": memory_id, "status": "ok"}
    except HTTPException:
        raise
    except ImportError as exc:
        logger.warning("mem0_runtime_missing", error=str(exc))
        raise HTTPException(status_code=424, detail="Mem0 runtime is not installed") from exc
    except Exception as exc:
        logger.warning("mem0_add_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Mem0 add failed") from exc


# ─── Pydantic-AI Endpoints ───

@router.post("/integrations/agent/run")
async def agent_run(
    payload: dict[str, Any],
    _auth: dict = Depends(require_admin()),
) -> dict[str, Any]:
    """Run a Pydantic-AI agent."""
    try:
        from app.core.integration.pydantic_ai_agent import create_agent

        prompt = payload.get("prompt", "")
        system_prompt = payload.get("system_prompt")
        model = payload.get("model", "gpt-4")

        agent = create_agent(
            system_prompt=system_prompt or "You are a helpful AI assistant.",
            model=model,
        )
        result = await agent.run(prompt)
        return {
            "content": result.content,
            "confidence": result.confidence,
            "tool_calls": result.tool_calls,
            "metadata": result.metadata,
            "status": "ok",
        }
    except Exception as exc:
        logger.warning("agent_run_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Agent execution failed") from exc

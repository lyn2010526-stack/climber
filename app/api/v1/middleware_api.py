"""Middleware & Metrics API — management and monitoring endpoints.

Provides:
- GET /api/v1/middleware/status — middleware stack status
- POST /api/v1/middleware/register — register a middleware
- DELETE /api/v1/middleware/{name} — unregister a middleware
- POST /api/v1/middleware/{name}/enable — enable a middleware
- POST /api/v1/middleware/{name}/disable — disable a middleware
- GET /api/v1/metrics — current metrics snapshot
- GET /api/v1/health — health check
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.auth import get_current_user

router = APIRouter(
    prefix="/middleware",
    tags=["middleware"],
    dependencies=[Depends(get_current_user)],
)


class MiddlewareRegisterRequest(BaseModel):
    """Request to register a middleware."""
    name: str
    class_path: str
    enabled: bool = True
    priority: int = 100
    config: dict | None = None


class MiddlewareStatusResponse(BaseModel):
    """Response for middleware status."""
    name: str
    enabled: bool
    hooks: list[str]
    call_count: int = 0
    error_count: int = 0


@router.get("/status")
async def get_middleware_status() -> list[MiddlewareStatusResponse]:
    """Get status of all registered middlewares."""
    from app.core.middleware_config import get_middleware_config_manager
    manager = get_middleware_config_manager()
    states = manager.get_state()
    return [MiddlewareStatusResponse(**s) for s in states]


@router.post("/register")
async def register_middleware(req: MiddlewareRegisterRequest) -> dict:
    """Register a new middleware."""
    from app.core.middleware_config import get_middleware_config_manager
    manager = get_middleware_config_manager()
    manager.register(
        name=req.name,
        class_path=req.class_path,
        enabled=req.enabled,
        priority=req.priority,
        config=req.config,
    )
    return {"status": "registered", "name": req.name}


@router.delete("/{name}")
async def unregister_middleware(name: str) -> dict:
    """Unregister a middleware."""
    from app.core.middleware_config import get_middleware_config_manager
    manager = get_middleware_config_manager()
    if manager.get_config(name) is None:
        raise HTTPException(status_code=404, detail=f"Middleware '{name}' not found")
    manager.unregister(name)
    return {"status": "unregistered", "name": name}


@router.post("/{name}/enable")
async def enable_middleware(name: str) -> dict:
    """Enable a middleware."""
    from app.core.middleware_config import get_middleware_config_manager
    manager = get_middleware_config_manager()
    if manager.get_config(name) is None:
        raise HTTPException(status_code=404, detail=f"Middleware '{name}' not found")
    manager.enable(name)
    return {"status": "enabled", "name": name}


@router.post("/{name}/disable")
async def disable_middleware(name: str) -> dict:
    """Disable a middleware."""
    from app.core.middleware_config import get_middleware_config_manager
    manager = get_middleware_config_manager()
    if manager.get_config(name) is None:
        raise HTTPException(status_code=404, detail=f"Middleware '{name}' not found")
    manager.disable(name)
    return {"status": "disabled", "name": name}


# ─── Config File Endpoints ──────────────────────────────────────────────

class ConfigImportRequest(BaseModel):
    """Request to import middleware config from a list of entries."""
    config: list[dict]


@router.post("/config/export")
async def export_config() -> list[dict]:
    """Export current middleware configuration."""
    from app.core.middleware_config import get_middleware_config_manager
    manager = get_middleware_config_manager()
    return manager.export_config()


@router.post("/config/import")
async def import_config(req: ConfigImportRequest) -> dict:
    """Import middleware configuration from a list of entries."""
    from app.core.middleware_config import get_middleware_config_manager
    manager = get_middleware_config_manager()
    imported = manager.import_config(req.config)
    return {"status": "imported", "count": imported}


# ─── Metrics Endpoints ──────────────────────────────────────────────────

metrics_router = APIRouter(
    prefix="/metrics",
    tags=["metrics"],
    dependencies=[Depends(get_current_user)],
)


@metrics_router.get("")
async def get_metrics() -> dict:
    """Get current metrics snapshot."""
    from app.core.metrics_collector import get_metrics_collector
    collector = get_metrics_collector()
    return collector.snapshot()


@metrics_router.post("/reset")
async def reset_metrics() -> dict:
    """Reset all metrics."""
    from app.core.metrics_collector import get_metrics_collector
    collector = get_metrics_collector()
    collector.reset()
    return {"status": "reset"}


# ─── Health Check Endpoints ─────────────────────────────────────────────

health_router = APIRouter(
    prefix="/health",
    tags=["health"],
)


@health_router.get("")
async def health_check() -> dict:
    """Full health check."""
    from app.core.health_check import get_health_checker
    checker = get_health_checker()
    return await checker.check()


@health_router.get("/ready")
async def readiness() -> dict:
    """Readiness probe."""
    from app.core.health_check import get_health_checker
    checker = get_health_checker()
    ready = await checker.readiness()
    return JSONResponse(
        status_code=status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"ready": ready},
    )


@health_router.get("/live")
async def liveness() -> dict:
    """Liveness probe."""
    from app.core.health_check import get_health_checker
    checker = get_health_checker()
    alive = await checker.liveness()
    return {"alive": alive}

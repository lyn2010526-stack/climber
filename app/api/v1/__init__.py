"""API v1 router aggregation."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import api_keys as api_keys_router
from app.api.v1 import auth_management as auth_management_router
from app.api.v1 import chat as chat_router
from app.api.v1 import cost as cost_router
from app.api.v1 import doctor as doctor_router
from app.api.v1 import documents as documents_router
from app.api.v1 import feedback as feedback_router
from app.api.v1 import generic as generic_router
from app.api.v1 import mcp as mcp_router
from app.api.v1 import notifications as notifications_router
from app.api.v1 import permissions as permissions_router
from app.api.v1 import prompt_templates as prompt_templates_router
from app.api.v1 import scheduler as scheduler_router
from app.api.v1 import sessions as sessions_router
from app.api.v1 import settings as settings_router
from app.api.v1 import skills_router as skills_router_module
from app.api.v1 import workflows as workflows_router
from app.core.reasoning import api as reasoning_router

router = APIRouter()
router.include_router(chat_router.router, prefix="/sessions", tags=["sessions"])
router.include_router(sessions_router.router, prefix="/sessions", tags=["sessions"])
router.include_router(auth_management_router.router)
router.include_router(settings_router.router, prefix="/settings", tags=["settings"])
router.include_router(workflows_router.router, prefix="/workflows", tags=["workflows"])
router.include_router(prompt_templates_router.router, prefix="/prompt-templates", tags=["prompt-templates"])
router.include_router(generic_router.router, tags=["generic"])
router.include_router(api_keys_router.router, prefix="/api-keys", tags=["api-keys"])
router.include_router(documents_router.router, prefix="/documents", tags=["documents"])
router.include_router(feedback_router.router, prefix="/feedback", tags=["feedback"])
router.include_router(notifications_router.router, prefix="/notifications", tags=["notifications"])
router.include_router(doctor_router.router, prefix="/doctor", tags=["doctor"])
router.include_router(reasoning_router.router, prefix="/reason", tags=["reasoning"])
router.include_router(permissions_router.router, prefix="/permissions", tags=["permissions"])


def _include_extension_routes(source: APIRouter, prefixes: tuple[str, ...]) -> None:
    for route in source.routes:
        path = getattr(route, "path", "")
        if path.startswith(prefixes):
            router.routes.append(route)


_include_extension_routes(cost_router.router, ("/cost/usage",))
_include_extension_routes(scheduler_router.router, ("/scheduler/tasks",))
_include_extension_routes(mcp_router.router, ("/mcp/servers", "/mcp/categories"))
_include_extension_routes(skills_router_module.router, ("/skills/autonomous",))

for route in skills_router_module.router.routes:
    if getattr(route, "path", "") == "/skills/{skill_id}" and "PATCH" in getattr(route, "methods", set()):
        router.routes.append(route)


@router.get("/health", tags=["system"])
async def api_health() -> dict:
    """API-level health check."""
    return {"status": "ok"}


def get_engine():
    from app.core.agent_engine import get_engine as _get_engine
    return _get_engine()

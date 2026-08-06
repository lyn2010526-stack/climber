"""Generic API endpoints backed by real database persistence.

This module serves as a central aggregation point for all domain-specific
route modules. Each endpoint performs real reads/writes against the database.

Routes are registered with and without a trailing slash because the app runs
with redirect_slashes=False.

Note: Route handlers have been extracted to app.api.v1.routes.* modules
for better maintainability. This file re-exports all routers.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes.agents import router as agents_router
from app.api.v1.routes.crews import router as crews_router
from app.api.v1.routes.groups import router as groups_router
from app.api.v1.routes.integrations import router as integrations_router
from app.api.v1.routes.misc import router as misc_router
from app.api.v1.routes.skills import router as skills_router
from app.api.v1.routes.tasks import router as tasks_router
from app.api.v1.routes.websocket import websocket_router
from app.api.v1.routes.workflows import router as workflows_router

router = APIRouter()

router.include_router(agents_router)
router.include_router(workflows_router)
router.include_router(crews_router)
router.include_router(skills_router)
router.include_router(groups_router)
router.include_router(tasks_router)
router.include_router(misc_router)
router.include_router(integrations_router)

# Expose WebSocket routes directly (not via include_router) so they appear as
# concrete APIWebSocketRoute entries on this router for runtime inspection.
for _ws_route in websocket_router.routes:
    router.routes.append(_ws_route)

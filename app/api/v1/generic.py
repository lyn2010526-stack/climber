"""Generic API endpoints backed by real database persistence.

Formerly a ~2250-line monolith; now an aggregator that mounts the domain
modules split out of it. Every endpoint performs real reads/writes. Request
bodies accept either a flat object (what the frontend sends) or a
{"data": {...}} envelope. Routes are registered with and without a trailing
slash because the app runs with redirect_slashes=False.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v1 import (
    agents_api,
    cluster_api,
    cost_api,
    eval_api,
    groups_api,
    misc_api,
    plugins_api,
    tasks_api,
    traces_api,
    workflows_api,
    ws,
)
from app.core.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])

router.include_router(agents_api.router)
router.include_router(workflows_api.router)
router.include_router(groups_api.router)
router.include_router(cluster_api.router)
router.include_router(plugins_api.router)
router.include_router(traces_api.router)
router.include_router(tasks_api.router)
router.include_router(eval_api.router)
router.include_router(cost_api.router)
router.include_router(misc_api.router)
router.include_router(ws.router)

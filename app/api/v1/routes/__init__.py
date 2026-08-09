"""API route modules organized by domain."""

from app.api.v1.routes.agents import router as agents_router
from app.api.v1.routes.crews import router as crews_router
from app.api.v1.routes.groups import router as groups_router
from app.api.v1.routes.misc import router as misc_router
from app.api.v1.routes.skills import router as skills_router
from app.api.v1.routes.tasks import router as tasks_router
from app.api.v1.routes.websocket import websocket_router
from app.api.v1.routes.workflows import router as workflows_router

__all__ = [
    "agents_router",
    "workflows_router",
    "crews_router",
    "skills_router",
    "groups_router",
    "tasks_router",
    "misc_router",
    "websocket_router",
]

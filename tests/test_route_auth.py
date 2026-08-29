"""Verify v1 routers carry the get_current_user auth dependency."""

from __future__ import annotations

from fastapi.routing import APIRoute

from app.api.v1 import (
    approvals,
    chat,
    crews,
    doctor,
    documents,
    feedback,
    generic,
    mcp,
    notifications,
    permissions,
    prompt_templates,
    scheduler,
    sessions,
    settings,
    skills_router,
    terminal,
    workflows,
)
from app.core.auth import get_current_user
from app.core.reasoning import api as reasoning_api

ROUTER_MODULES = [
    approvals,
    chat,
    crews,
    doctor,
    documents,
    feedback,
    generic,
    mcp,
    notifications,
    permissions,
    prompt_templates,
    scheduler,
    sessions,
    settings,
    skills_router,
    terminal,
    workflows,
    reasoning_api,
]


def _iter_http_routes(routes):
    from fastapi.routing import _IncludedRouter

    for route in routes:
        if isinstance(route, _IncludedRouter):
            yield from _iter_http_routes(route.original_router.routes)
        elif isinstance(route, APIRoute):
            yield route


def _route_has_auth(route) -> bool:
    if not isinstance(route, APIRoute):
        return True
    calls = [getattr(d, "dependency", None) for d in route.dependencies]
    calls += [d.call for d in route.dependant.dependencies]
    return get_current_user in calls


def test_all_v1_routers_have_auth_dependency():
    total = 0
    for module in ROUTER_MODULES:
        router = module.router
        router_level = get_current_user in [
            getattr(d, "dependency", None) for d in router.dependencies
        ]
        checked = 0
        for route in _iter_http_routes(router.routes):
            checked += 1
            assert router_level or _route_has_auth(route), (
                f"{module.__name__}: route {route.path} lacks get_current_user"
            )
        assert checked > 0, f"{module.__name__} has no HTTP routes"
        total += checked
    assert total > 100


def test_generic_run_workflow_keeps_user_param():
    run_routes = [
        r
        for r in _iter_http_routes(generic.router.routes)
        if "run" in r.path
    ]
    assert run_routes, "run_workflow route not found"
    found = False
    for route in run_routes:
        for d in route.dependant.dependencies:
            if d.call is get_current_user:
                found = True
    assert found, "run_workflow route-level user dependency missing"

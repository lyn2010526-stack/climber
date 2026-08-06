"""Collaboration API — FastAPI router for collaboration layer endpoints.

Provides REST endpoints for handoff management, role queries,
and result aggregation with authentication required.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.core.collaboration import (
    AggregationStrategy,
    HandoffManager,
    ResultAggregator,
    RoleRegistry,
)

router = APIRouter(
    prefix="/api/v1/collaboration",
    tags=["collaboration"],
    redirect_slashes=False,
)

_handoff_manager = HandoffManager()
_role_registry = RoleRegistry()
_result_aggregator = ResultAggregator()


def get_handoff_manager() -> HandoffManager:
    return _handoff_manager


def get_role_registry() -> RoleRegistry:
    return _role_registry


def get_result_aggregator() -> ResultAggregator:
    return _result_aggregator


@router.post("/handoffs")
async def create_handoff(
    task_id: str,
    from_agent_id: str,
    to_agent_id: str,
    context: dict[str, Any] | None = None,
    priority: int = 0,
    manager: HandoffManager = Depends(get_handoff_manager),
) -> dict[str, Any]:
    """Create a new handoff request."""
    handoff = manager.request_handoff(
        task_id=task_id,
        from_agent_id=from_agent_id,
        to_agent_id=to_agent_id,
        context=context,
        priority=priority,
    )
    return handoff.to_dict()


@router.get("/handoffs")
async def list_handoffs(
    agent_id: str | None = None,
    manager: HandoffManager = Depends(get_handoff_manager),
) -> list[dict[str, Any]]:
    """List pending handoffs, optionally filtered by target agent."""
    handoffs = manager.get_pending_handoffs(agent_id=agent_id)
    return [h.to_dict() for h in handoffs]


@router.post("/handoffs/{handoff_id}/accept")
async def accept_handoff(
    handoff_id: str,
    manager: HandoffManager = Depends(get_handoff_manager),
) -> dict[str, Any]:
    """Accept a pending handoff request."""
    handoff = manager.accept_handoff(handoff_id)
    if not handoff:
        raise HTTPException(status_code=404, detail="Handoff not found or not pending")
    return handoff.to_dict()


@router.post("/handoffs/{handoff_id}/reject")
async def reject_handoff(
    handoff_id: str,
    reason: str = "",
    manager: HandoffManager = Depends(get_handoff_manager),
) -> dict[str, Any]:
    """Reject a pending handoff request."""
    handoff = manager.reject_handoff(handoff_id, reason=reason)
    if not handoff:
        raise HTTPException(status_code=404, detail="Handoff not found or not pending")
    return handoff.to_dict()


@router.get("/roles")
async def list_roles(
    registry: RoleRegistry = Depends(get_role_registry),
) -> list[dict[str, Any]]:
    """List all registered roles and their capabilities."""
    roles = []
    for role in registry.list_roles():
        definition = registry.get_role_definition(role)
        if definition:
            roles.append({
                "role": role.value,
                "capabilities": [c.to_dict() for c in definition.capabilities],
                "allowed_tools": definition.allowed_tools,
                "allowed_actions": definition.allowed_actions,
                "max_iterations": definition.max_iterations,
            })
    return roles


@router.get("/aggregate/{task_id}")
async def get_aggregation(
    task_id: str,
    strategy: AggregationStrategy = AggregationStrategy.BEST_CONFIDENCE,
    aggregator: ResultAggregator = Depends(get_result_aggregator),
) -> dict[str, Any]:
    """Get aggregated result for a task."""
    result = aggregator.aggregate(task_id, strategy=strategy)
    return result.to_dict()

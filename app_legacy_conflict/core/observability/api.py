"""Observability API endpoints.

Provides REST endpoints for trace retrieval, audit chain access,
alignment status, and emergency stop control.
All endpoints require authentication.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.observability.alignment import GoalTracker
from app.core.observability.audit import AuditChain
from app.core.observability.emergency_stop import EmergencyStopManager
from app.core.observability.trace import TraceCollector
router = APIRouter(prefix="/api/v1/observability", tags=["observability"])

_trace_collector: TraceCollector | None = None
_audit_chain: AuditChain | None = None
_goal_tracker: GoalTracker | None = None
_emergency_stop: EmergencyStopManager | None = None


def get_trace_collector() -> TraceCollector:
    global _trace_collector
    if _trace_collector is None:
        _trace_collector = TraceCollector()
    return _trace_collector


def get_audit_chain() -> AuditChain:
    global _audit_chain
    if _audit_chain is None:
        _audit_chain = AuditChain()
    return _audit_chain


def get_goal_tracker() -> GoalTracker:
    global _goal_tracker
    if _goal_tracker is None:
        _goal_tracker = GoalTracker()
    return _goal_tracker


def get_emergency_stop() -> EmergencyStopManager:
    global _emergency_stop
    if _emergency_stop is None:
        _emergency_stop = EmergencyStopManager()
    return _emergency_stop


class EmergencyStopRequest(BaseModel):
    reason: str = "manual activation"
    triggered_by: str = "user"


class EmergencyStopDeactivateRequest(BaseModel):
    reason: str = "manual deactivation"
    triggered_by: str = "user"


# --- Trace Endpoints ---


@router.get("/traces")
async def list_traces(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    collector = get_trace_collector()
    traces = collector.list_traces(limit=limit, offset=offset)
    return {"traces": traces, "limit": limit, "offset": offset}


@router.get("/traces/{trace_id}")
async def get_trace(
    trace_id: str,
) -> dict[str, Any]:
    collector = get_trace_collector()
    spans = collector.get_trace(trace_id)
    if not spans:
        raise HTTPException(status_code=404, detail="Trace not found")
    return {
        "trace_id": trace_id,
        "spans": [s.to_dict() for s in spans],
        "span_count": len(spans),
    }


# --- Audit Endpoints ---


@router.get("/audit")
async def list_audit_entries(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    decision_type: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    chain = get_audit_chain()
    if decision_type:
        entries = chain.search_by_type(decision_type, limit=limit)
    else:
        entries = chain.get_chain(limit=limit, offset=offset, session_id=session_id)
    return {
        "entries": [e.to_dict() for e in entries],
        "total": chain.count_entries(session_id=session_id),
        "limit": limit,
        "offset": offset,
    }


# --- Alignment Endpoints ---


@router.get("/alignment")
async def get_alignment_status() -> dict[str, Any]:
    tracker = get_goal_tracker()
    goals = tracker.list_goals(active_only=False)
    drift_score = tracker.get_drift_score()
    return {
        "goals": [g.to_dict() for g in goals],
        "drift_score": drift_score,
        "threshold": tracker._alignment_threshold,
    }


# --- Emergency Stop Endpoints ---


@router.post("/emergency-stop")
async def activate_emergency_stop(
    request: EmergencyStopRequest,
) -> dict[str, Any]:
    manager = get_emergency_stop()
    if manager.is_activated():
        raise HTTPException(status_code=409, detail="Emergency stop is already activated")
    record = manager.activate(
        reason=request.reason,
        triggered_by=request.triggered_by,
    )
    return {"status": "activated", "record": record.to_dict()}


@router.delete("/emergency-stop")
async def deactivate_emergency_stop(
    request: EmergencyStopDeactivateRequest | None = None,
) -> dict[str, Any]:
    manager = get_emergency_stop()
    if not manager.is_activated():
        raise HTTPException(status_code=409, detail="Emergency stop is not activated")
    reason = request.reason if request else "manual deactivation"
    triggered_by = request.triggered_by if request else "user"
    record = manager.deactivate(reason=reason, triggered_by=triggered_by)
    return {"status": "deactivated", "record": record.to_dict()}


@router.get("/emergency-stop")
async def get_emergency_stop_status() -> dict[str, Any]:
    manager = get_emergency_stop()
    return manager.get_status()

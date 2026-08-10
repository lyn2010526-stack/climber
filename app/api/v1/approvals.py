"""Human-in-the-loop approval API.

Surfaces the in-process ApprovalManager so the frontend can list pending
tool-permission requests and resolve them (approve / reject).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.approval import approval_manager

router = APIRouter()


def _request_to_dict(req: Any) -> dict[str, Any]:
    return {
        "id": req.id,
        "session_id": req.session_id,
        "tool_name": req.tool_name,
        "arguments": req.arguments,
        "status": req.status.value if hasattr(req.status, "value") else str(req.status),
        "created_at": req.created_at.isoformat() if req.created_at else "",
        "resolved_at": req.resolved_at.isoformat() if req.resolved_at else None,
        "resolved_by": req.resolved_by,
        "reason": req.reason,
    }


@router.get("/")
async def list_approvals(session_id: str | None = None) -> dict[str, Any]:
    manager = approval_manager
    items = [_request_to_dict(r) for r in manager.get_pending(session_id=session_id)]
    return {"requests": items, "total": len(items)}


@router.get("/pending")
async def list_pending(session_id: str | None = None) -> dict[str, Any]:
    return await list_approvals(session_id=session_id)


class ApproveRequest(BaseModel):
    request_id: str
    reason: str = ""


@router.post("/approve")
async def approve_request(payload: ApproveRequest) -> dict[str, Any]:
    manager = approval_manager
    req = manager.approve(payload.request_id, resolved_by="human")
    if req is None:
        raise HTTPException(status_code=404, detail="Approval request not found or already resolved")
    return {"ok": True, "request": _request_to_dict(req)}


@router.post("/reject")
async def reject_request(payload: ApproveRequest) -> dict[str, Any]:
    manager = approval_manager
    req = manager.reject(payload.request_id, reason=payload.reason, resolved_by="human")
    if req is None:
        raise HTTPException(status_code=404, detail="Approval request not found or already resolved")
    return {"ok": True, "request": _request_to_dict(req)}


@router.get("/requests")
async def list_all_requests(limit: int = 50) -> dict[str, Any]:
    """List all tracked approval requests (pending + resolved), newest first."""
    manager = approval_manager
    all_reqs = manager.list_all()
    items = [_request_to_dict(r) for r in all_reqs[:limit]]
    return {"requests": items, "total": len(all_reqs)}

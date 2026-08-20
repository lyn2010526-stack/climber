"""Human-in-the-loop approval API backed by durable approval records."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.approval import approval_manager
from app.core.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


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
async def list_approvals(
    session_id: str | None = None,
    user_id: str = Depends(get_current_user),
) -> dict[str, Any]:
    manager = approval_manager
    items = [
        _request_to_dict(r)
        for r in await manager.get_pending_async(session_id=session_id, user_id=user_id)
    ]
    return {"requests": items, "total": len(items)}


@router.get("/pending")
async def list_pending(
    session_id: str | None = None,
    user_id: str = Depends(get_current_user),
) -> dict[str, Any]:
    return await list_approvals(session_id=session_id, user_id=user_id)


class ApproveRequest(BaseModel):
    request_id: str
    reason: str = ""


@router.post("/approve")
async def approve_request(
    payload: ApproveRequest,
    user_id: str = Depends(get_current_user),
) -> dict[str, Any]:
    manager = approval_manager
    req = await manager.approve_async(payload.request_id, resolved_by="human", user_id=user_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Approval request not found or already resolved")
    return {"ok": True, "request": _request_to_dict(req)}


@router.post("/reject")
async def reject_request(
    payload: ApproveRequest,
    user_id: str = Depends(get_current_user),
) -> dict[str, Any]:
    manager = approval_manager
    req = await manager.reject_async(
        payload.request_id,
        reason=payload.reason,
        resolved_by="human",
        user_id=user_id,
    )
    if req is None:
        raise HTTPException(status_code=404, detail="Approval request not found or already resolved")
    return {"ok": True, "request": _request_to_dict(req)}


@router.get("/requests")
async def list_all_requests(
    limit: int = Query(default=50, ge=1, le=200),
    user_id: str = Depends(get_current_user),
) -> dict[str, Any]:
    """List all tracked approval requests (pending + resolved), newest first."""
    manager = approval_manager
    all_reqs = await manager.list_all_async(limit=limit, user_id=user_id)
    total = await manager.count_async(user_id=user_id)
    items = [_request_to_dict(r) for r in all_reqs]
    return {"requests": items, "total": total}

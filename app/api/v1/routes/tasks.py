"""Task execution API — submit, query, cancel long-running tasks."""
from __future__ import annotations

import asyncio
import json
from contextlib import suppress
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import settings
from app.core.auth_manager import require_scopes
from app.core.task_worker import task_manager
from app.schemas.api_v1.tasks import SubmitTaskRequest

router = APIRouter(prefix="/tasks", tags=["tasks"])


class ClaimSubtasksRequest(BaseModel):
    agent_id: str
    limit: int = 1
    lease_seconds: int = 900


class CompleteSubtaskRequest(BaseModel):
    agent_id: str
    result: Any = None
    error: str | None = None


class TaskResponse(BaseModel):
    task_id: str
    objective: str = ""
    status: str
    progress: int = 0
    total_steps: int = 0
    result: Any = None
    error: str | None = None
    retry_count: int = 0
    checkpoint: dict[str, Any] | None = None
    progress_evaluation: dict[str, Any] | None = None
    interruption_reason: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None


_ws_clients: list[WebSocket] = []


async def _ws_broadcast(task_id: str, data: dict):
    """Broadcast task progress to all connected WebSocket clients."""
    import json
    msg = json.dumps({"task_id": task_id, **data})
    disconnected = []
    for ws in _ws_clients:
        try:
            await ws.send_text(msg)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        with suppress(ValueError):
            _ws_clients.remove(ws)


task_manager.on_progress(_ws_broadcast)


@router.post("/submit", response_model=TaskResponse)
async def submit_task(req: SubmitTaskRequest, _auth: dict = Depends(require_scopes("write"))):
    """Submit a new long-running task."""
    try:
        task_id = await task_manager.submit(req.task_type, req.payload, owner_id=_auth["id"])
        return TaskResponse(task_id=task_id, status="pending")
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, _auth: dict = Depends(require_scopes("read"))):
    """Get task status and result."""
    info = await task_manager.get_status(
        task_id,
        owner_id=_auth["id"],
        include_all=_auth.get("role") == "admin" or "admin" in _auth.get("scopes", []),
    )
    if not info:
        raise HTTPException(404, "Task not found")
    return TaskResponse(**info)


@router.get("/")
async def list_tasks(
    status_filter: str | None = None,
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    _auth: dict = Depends(require_scopes("read")),
):
    """List recent tasks, optionally filtered by status."""
    return await task_manager.list_tasks(
        status_filter or status,
        limit,
        owner_id=_auth["id"],
        include_all=_auth.get("role") == "admin" or "admin" in _auth.get("scopes", []),
    )


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str, _auth: dict = Depends(require_scopes("write"))):
    """Cancel a running task. Owners may cancel their own tasks; admins may cancel any."""
    is_admin = _auth.get("role") == "admin" or "admin" in _auth.get("scopes", [])
    record = await task_manager.get_status(
        task_id, owner_id=_auth["id"], include_all=is_admin
    )
    if record is None:
        raise HTTPException(404, "Task not found")
    success = await task_manager.cancel(task_id)
    if not success:
        raise HTTPException(400, "Task not running or not found")
    return {"task_id": task_id, "cancelled": True}


async def _control(task_id: str, action: str, auth: dict) -> dict[str, Any]:
    is_admin = auth.get("role") == "admin" or "admin" in auth.get("scopes", [])
    if await task_manager.get_status(task_id, owner_id=auth["id"], include_all=is_admin) is None:
        raise HTTPException(404, "Task not found")
    ok = await getattr(task_manager, action)(task_id)
    if not ok:
        raise HTTPException(409, f"Task cannot be {action}")
    return {"task_id": task_id, action: True}


@router.post("/{task_id}/pause")
async def pause_task(task_id: str, _auth: dict = Depends(require_scopes("write"))):
    return await _control(task_id, "pause", _auth)


@router.post("/{task_id}/resume")
async def resume_task(task_id: str, _auth: dict = Depends(require_scopes("write"))):
    return await _control(task_id, "resume", _auth)


@router.post("/{task_id}/retry")
async def retry_task(task_id: str, _auth: dict = Depends(require_scopes("write"))):
    return await _control(task_id, "retry", _auth)


@router.post("/{task_id}/rollback")
async def rollback_task(task_id: str, _auth: dict = Depends(require_scopes("write"))):
    return await _control(task_id, "rollback", _auth)


@router.get("/{task_id}/events")
async def task_events(task_id: str, _auth: dict = Depends(require_scopes("read"))):
    is_admin = _auth.get("role") == "admin" or "admin" in _auth.get("scopes", [])
    if await task_manager.get_status(task_id, owner_id=_auth["id"], include_all=is_admin) is None:
        raise HTTPException(404, "Task not found")
    queue = task_manager.subscribe(task_id, replay=False)

    async def stream():
        try:
            snapshot = await task_manager.event_snapshot(task_id, _auth["id"], is_admin)
            if snapshot is None:
                return
            yield f"data: {json.dumps(snapshot, ensure_ascii=False)}\n\n"
            if snapshot["data"]["status"] in {"completed", "failed", "cancelled"}:
                return
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if event.get("data", {}).get("status") in {"completed", "failed", "cancelled"}:
                    break
        finally:
            task_manager.unsubscribe(task_id, queue)

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/{task_id}/snapshot")
async def task_snapshot(task_id: str, _auth: dict = Depends(require_scopes("read"))):
    snapshot = await task_manager.event_snapshot(
        task_id, _auth["id"], _auth.get("role") == "admin" or "admin" in _auth.get("scopes", []),
    )
    if snapshot is None:
        raise HTTPException(404, "Task not found")
    return snapshot


@router.get("/{task_id}/subtasks")
async def list_subtasks(task_id: str, status: str | None = None, _auth: dict = Depends(require_scopes("read"))):
    """List persisted subtasks, optionally filtered by lifecycle status."""
    is_admin = _auth.get("role") == "admin" or "admin" in _auth.get("scopes", [])
    subtasks = await task_manager.list_subtasks(task_id, owner_id=_auth["id"], include_all=is_admin, status=status)
    if subtasks is None:
        raise HTTPException(404, "Task not found")
    return {"task_id": task_id, "subtasks": subtasks}


@router.post("/{task_id}/subtasks/claim")
async def claim_subtasks(task_id: str, req: ClaimSubtasksRequest, _auth: dict = Depends(require_scopes("write"))):
    """Claim ready subtasks with a compare-and-set update."""
    if not 1 <= req.limit <= 50 or not 1 <= req.lease_seconds <= 86400:
        raise HTTPException(422, "limit must be 1..50 and lease_seconds must be 1..86400")
    is_admin = _auth.get("role") == "admin" or "admin" in _auth.get("scopes", [])
    subtasks = await task_manager.claim_subtasks(
        task_id, owner_id=_auth["id"], agent_id=req.agent_id, limit=req.limit,
        include_all=is_admin, lease_seconds=req.lease_seconds,
    )
    if subtasks is None:
        raise HTTPException(404, "Task not found")
    return {"task_id": task_id, "subtasks": subtasks}


@router.post("/{task_id}/subtasks/{subtask_id}/complete")
async def complete_subtask(task_id: str, subtask_id: str, req: CompleteSubtaskRequest, _auth: dict = Depends(require_scopes("write"))):
    """Report a subtask result; only the claiming agent may complete it."""
    is_admin = _auth.get("role") == "admin" or "admin" in _auth.get("scopes", [])
    subtask = await task_manager.complete_subtask(
        task_id, subtask_id, owner_id=_auth["id"], agent_id=req.agent_id,
        result=req.result, error=req.error, include_all=is_admin,
    )
    if subtask is None:
        raise HTTPException(409, "Subtask is missing, already completed, or owned by another agent")
    return subtask


@router.websocket("/ws")
async def task_websocket(websocket: WebSocket):
    """WebSocket for real-time task progress notifications."""
    from app.middleware.auth import authenticate_credentials

    if settings.enable_auth:
        try:
            auth = await authenticate_credentials(websocket.headers)
        except HTTPException:
            auth = None
        if auth is None:
            await websocket.close(code=4401, reason="Authentication required")
            return
        scopes = auth.get("scopes", [])
        if auth.get("role") != "admin" and "admin" not in scopes:
            await websocket.close(code=4403, reason="Admin scope required")
            return
    await websocket.accept()
    _ws_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in _ws_clients:
            _ws_clients.remove(websocket)

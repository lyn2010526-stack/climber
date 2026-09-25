"""Task execution API — submit, query, cancel long-running tasks."""
from __future__ import annotations

from contextlib import suppress
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.config import settings
from app.core.auth_manager import require_scopes
from app.core.task_worker import task_manager

router = APIRouter(prefix="/tasks", tags=["tasks"])


class SubmitTaskRequest(BaseModel):
    task_type: str
    payload: dict[str, Any] = {}


class TaskResponse(BaseModel):
    task_id: str
    objective: str = ""
    status: str
    progress: int = 0
    total_steps: int = 0
    result: Any = None
    error: str | None = None


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

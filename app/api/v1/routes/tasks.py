"""Task execution API — submit, query, cancel long-running tasks."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Any

from app.core.task_worker import task_manager, TaskStatus

router = APIRouter(prefix="/tasks", tags=["tasks"])


class SubmitTaskRequest(BaseModel):
    task_type: str
    payload: dict[str, Any] = {}


class TaskResponse(BaseModel):
    task_id: str
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
    for ws in _ws_clients:
        try:
            _ws_clients.remove(ws)
        except ValueError:
            pass


task_manager.on_progress(_ws_broadcast)


@router.post("/submit", response_model=TaskResponse)
async def submit_task(req: SubmitTaskRequest):
    """Submit a new long-running task."""
    try:
        task_id = await task_manager.submit(req.task_type, req.payload)
        return TaskResponse(task_id=task_id, status="pending")
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """Get task status and result."""
    info = await task_manager.get_status(task_id)
    if not info:
        raise HTTPException(404, "Task not found")
    return TaskResponse(**info)


@router.get("/")
async def list_tasks(status_filter: str | None = None, limit: int = 50):
    """List recent tasks, optionally filtered by status."""
    return await task_manager.list_tasks(status_filter, limit)


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str):
    """Cancel a running task."""
    success = await task_manager.cancel(task_id)
    if not success:
        raise HTTPException(400, "Task not running or not found")
    return {"task_id": task_id, "cancelled": True}


@router.websocket("/ws")
async def task_websocket(websocket: WebSocket):
    """WebSocket for real-time task progress notifications."""
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

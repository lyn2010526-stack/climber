"""Task execution API — submit, query, cancel long-running tasks."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy import select

from app.config import settings
from app.core import task_worker as task_worker_module
from app.core.auth import LOCAL_USER_ID
from app.core.auth_manager import require_scopes
from app.core.task_worker import task_manager
from app.middleware.auth import authenticate_credentials
from app.storage.database import Session
from app.storage.models_platform import AutoLoopTask, Workflow

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


_ws_clients: dict[WebSocket, str] = {}


def _task_session() -> Any:
    """Return the session factory the task worker writes task rows with.

    Task rows are owned by the task worker, so every read on this router goes
    through the same factory the worker uses instead of binding a second
    reference to the storage module.
    """
    return task_worker_module.async_session()


async def _ws_broadcast(task_id: str, data: dict):
    """Broadcast task progress to all connected WebSocket clients."""
    msg = json.dumps({"task_id": task_id, **data})
    disconnected = []
    for ws, subscribed_task_id in list(_ws_clients.items()):
        if subscribed_task_id != task_id:
            continue
        try:
            await ws.send_text(msg)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        _ws_clients.pop(ws, None)


task_manager.on_progress(_ws_broadcast)


@router.post("/submit", response_model=TaskResponse)
async def submit_task(req: SubmitTaskRequest, _auth: dict = Depends(require_scopes("write"))):
    """Submit a new long-running task."""
    try:
        owner_id = str(_auth.get("user_id") or _auth.get("id"))
        payload = {**req.payload, "_owner_id": owner_id}
        await _ensure_owned_resources(payload, owner_id)
        task_id = await task_manager.submit(req.task_type, payload)
        return TaskResponse(task_id=task_id, status="pending")
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, _auth: dict = Depends(require_scopes("read"))):
    """Get task status and result."""
    owner_id = str(_auth.get("user_id") or _auth.get("id"))
    async with _task_session() as db:
        record = await _owned_task(db, task_id, owner_id)
        if record is None:
            raise HTTPException(404, "Task not found")
        return TaskResponse(**_task_response(record))


@router.get("/")
async def list_tasks(
    status_filter: str | None = None,
    status: str | None = None,
    limit: int = 50,
    _auth: dict = Depends(require_scopes("read")),
):
    """List recent tasks, optionally filtered by status."""
    owner_id = str(_auth.get("user_id") or _auth.get("id"))
    async with _task_session() as db:
        stmt = select(AutoLoopTask).order_by(AutoLoopTask.created_at.desc()).limit(limit)
        if status_filter or status:
            stmt = stmt.where(AutoLoopTask.status == (status_filter or status))
        records = (await db.execute(stmt)).scalars().all()
        return [_task_summary(record) for record in records if _task_owner(record) == owner_id]


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str, _auth: dict = Depends(require_scopes("write"))):
    """Cancel a running task. Owners may cancel their own tasks; admins may cancel any."""
    owner_id = str(_auth.get("user_id") or _auth.get("id"))
    is_admin = _auth.get("role") == "admin" or "admin" in _auth.get("scopes", [])
    async with _task_session() as db:
        if await _owned_task(db, task_id, owner_id, include_all=is_admin) is None:
            raise HTTPException(404, "Task not found")
    success = await task_manager.cancel(task_id)
    if not success:
        raise HTTPException(400, "Task not running or not found")
    return {"task_id": task_id, "cancelled": True}


@router.websocket("/ws")
async def task_websocket(websocket: WebSocket):
    """WebSocket for real-time task progress notifications."""
    task_id = websocket.query_params.get("task_id")
    user_id = await _authenticate_task_websocket(websocket, task_id)
    if user_id is None or task_id is None:
        return

    await websocket.accept()
    _ws_clients[websocket] = task_id
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.pop(websocket, None)


async def _ensure_owned_resources(payload: dict[str, Any], owner_id: str) -> None:
    """Reject task references to sessions or workflows owned by another user."""
    async with _task_session() as db:
        session_id = payload.get("session_id")
        if session_id:
            session = await db.scalar(select(Session).where(Session.id == str(session_id)))
            if session is None or str(session.user_id) != owner_id:
                raise ValueError("Session not found")

        workflow_id = payload.get("workflow_id")
        if workflow_id:
            workflow = await db.scalar(select(Workflow).where(Workflow.id == str(workflow_id)))
            if workflow is None or str(workflow.user_id) != owner_id:
                raise ValueError("Workflow not found")


def _task_owner(record: AutoLoopTask) -> str | None:
    if record.owner_id:
        return str(record.owner_id)
    references = _task_references(record.objective)
    owner_id = references.get("_owner_id")
    return str(owner_id) if owner_id else None


async def _owned_task(
    db: Any, task_id: str, owner_id: str, include_all: bool = False
) -> AutoLoopTask | None:
    record = await db.scalar(select(AutoLoopTask).where(AutoLoopTask.id == task_id))
    if record is None or (not include_all and _task_owner(record) != owner_id):
        return None
    return record


def _task_response(record: AutoLoopTask) -> dict[str, Any]:
    return {
        "task_id": record.id,
        "objective": task_manager._objective_from_record(record.objective),
        "status": record.status,
        "progress": record.current_step,
        "total_steps": record.max_steps,
        "result": record.result,
        "error": record.error,
    }


def _task_summary(record: AutoLoopTask) -> dict[str, Any]:
    return {
        "task_id": record.id,
        "objective": task_manager._objective_from_record(record.objective)[:100],
        "status": record.status,
        "progress": record.current_step,
        "total_steps": record.max_steps,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


def _task_references(raw_objective: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw_objective)
    except (TypeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


async def _authenticate_task_websocket(websocket: WebSocket, task_id: str | None) -> str | None:
    """Authenticate and authorize a task-specific progress socket before accepting it."""
    if not settings.enable_auth:
        user_id = LOCAL_USER_ID
    else:
        try:
            auth = await authenticate_credentials(
                websocket.headers,
                token=websocket.cookies.get("access_token"),
            )
        except HTTPException:
            await websocket.close(code=1008)
            return None
        user_id = str(auth.get("sub") or auth.get("owner")) if auth else ""

    if not task_id or not user_id:
        await websocket.close(code=1008)
        return None

    async with _task_session() as db:
        task = await db.scalar(select(AutoLoopTask).where(AutoLoopTask.id == task_id))
        if task is None:
            await websocket.close(code=1008)
            return None
        references = _task_references(task.objective)
        if str(references.get("_owner_id", "")) != user_id:
            await websocket.close(code=1008)
            return None
        try:
            await _ensure_owned_resources(references, user_id)
        except ValueError:
            await websocket.close(code=1008)
            return None

    return user_id

"""WebSocket endpoints (session echo, group chat, task live status, collab).

Split out of the former monolithic generic API module (pure move refactor).
WS endpoints authenticate via authenticate_websocket instead of the router-level
get_current_user dependency.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter
from sqlalchemy import select
from starlette.websockets import WebSocket

from app.core.auth import authenticate_websocket
from app.storage import async_session
from app.storage.models_groups import AgentGroup, AgentGroupTask

router = APIRouter()
logger = structlog.get_logger()

# ─── Session echo WebSocket ─────────────────────────────────────────────────


@router.websocket("/ws/{session_id}")
async def ws_endpoint(websocket: WebSocket, session_id: str):
    if await authenticate_websocket(websocket) is None:
        return
    await websocket.accept()
    await websocket.send_json({"type": "connected", "session_id": session_id})
    try:
        while True:
            msg = await websocket.receive_text()
            await websocket.send_json({"type": "echo", "data": msg})
    except Exception as e:
        logger.warning("ws.endpoint_disconnect", error=str(e))
    finally:
        try:
            await websocket.close()
        except Exception as e:
            logger.warning("ws.endpoint_close", error=str(e))


# ─── Group chat WebSocket ───────────────────────────────────────────────────


@router.websocket("/ws/groups/{group_id}")
async def ws_group_endpoint(websocket: WebSocket, group_id: str):
    from app.core.group_ws_hub import group_ws_hub

    user_id = await authenticate_websocket(websocket)
    if user_id is None:
        return

    await websocket.accept()

    async with async_session() as db:
        group = (await db.execute(select(AgentGroup).where(AgentGroup.id == group_id))).scalar_one_or_none()
        if group is None:
            await websocket.send_json({"type": "error", "error": "group_not_found"})
            await websocket.close()
            return

    await group_ws_hub.connect(group_id, websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "error": "invalid_json"})
                continue
            if payload.get("type") == "message":
                payload.setdefault("sender_id", user_id)
            result = await group_ws_hub.handle_message(group_id, payload)
            await websocket.send_json({"type": "ack", "data": result})
    except Exception as e:
        logger.warning("ws.group_endpoint_disconnect", error=str(e))
    finally:
        await group_ws_hub.disconnect(group_id, websocket)
        try:
            await websocket.close()
        except Exception as e:
            logger.warning("ws.group_endpoint_close", error=str(e))

# ─── Task live status WebSocket ─────────────────────────────────────────────

_task_ws_connections: dict[str, set[WebSocket]] = {}


async def _task_to_ws_payload(task: AgentGroupTask) -> dict[str, Any]:
    return {
        "id": task.id,
        "group_id": task.group_id,
        "description": task.description,
        "status": task.status,
        "worker_id": task.worker_id,
        "reviewer_ids": task.reviewer_ids or [],
        "current_round": task.current_round,
        "max_rounds": task.max_rounds,
        "human_review_required": getattr(task, "human_review_required", False),
        "human_review_status": getattr(task, "human_review_status", "pending"),
        "final_output": task.final_output or "",
        "total_tokens": task.total_tokens or 0,
        "created_at": task.created_at.isoformat() if task.created_at else "",
        "started_at": task.started_at.isoformat() if task.started_at else "",
        "completed_at": task.completed_at.isoformat() if task.completed_at else "",
    }


@router.websocket("/ws/task/{task_id}")
async def ws_task_endpoint(websocket: WebSocket, task_id: str):
    """Live task status stream for the task monitor page.

    On connect: pushes the current task snapshot as a `task_state` event.
    Connection stays open; clients may send {"type":"ping"} and receive pong.
    Task state changes are pushed by _broadcast_task_update.
    """
    if await authenticate_websocket(websocket) is None:
        return
    await websocket.accept()
    _task_ws_connections.setdefault(task_id, set()).add(websocket)
    try:
        async with async_session() as db:
            task = (await db.execute(select(AgentGroupTask).where(AgentGroupTask.id == task_id))).scalar_one_or_none()
            if task is None:
                await websocket.send_json({"type": "error", "error": "task_not_found", "task_id": task_id})
            else:
                await websocket.send_json({"type": "task_state", "task": await _task_to_ws_payload(task)})
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "error": "invalid_json"})
                continue
            if payload.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except Exception as e:
        logger.warning("generic.ws_task_endpoint_disconnect", error=str(e))
    finally:
        conns = _task_ws_connections.get(task_id)
        if conns:
            conns.discard(websocket)
            if not conns:
                _task_ws_connections.pop(task_id, None)
        try:
            await websocket.close()
        except Exception as e:
            logger.warning("generic.ws_task_endpoint_close", error=str(e))


async def _broadcast_task_update(task_id: str, payload: dict[str, Any]) -> None:
    """Push a task_state event to all subscribers of a task channel."""
    conns = list(_task_ws_connections.get(task_id, set()))
    for ws in conns:
        try:
            await ws.send_json({"type": "task_state", "task": payload})
        except Exception as e:
            logger.debug("generic.task_ws_send_failed", task_id=task_id, error=str(e))


# ─── Collaboration session WebSocket ────────────────────────────────────────

_collab_ws_connections: dict[str, set[WebSocket]] = {}


@router.websocket("/ws/collab/{session_id}")
async def ws_collab_endpoint(websocket: WebSocket, session_id: str):
    """Real-time collaboration channel for a session.

    Supports the useCollaborationWebSocket client contract:
      - {"type": "hello", "token": ...} -> {"type": "hello", "session_id": ...}
      - {"type": "ping"} -> {"type": "pong"}
      - {"type": "message", "content": ...} -> broadcast {"type": "message", ...}
      - any other {"type": "broadcast", "data": ...} -> relayed to peers
    """
    user_id = await authenticate_websocket(websocket)
    if user_id is None:
        return
    await websocket.accept()
    _collab_ws_connections.setdefault(session_id, set()).add(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "error": "invalid_json"})
                continue
            msg_type = payload.get("type", "")
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg_type == "hello":
                await websocket.send_json({"type": "hello", "session_id": session_id, "user_id": user_id})
            elif msg_type == "message":
                message = {
                    "type": "message",
                    "session_id": session_id,
                    "sender_id": payload.get("sender_id") or user_id,
                    "content": payload.get("content", ""),
                    "ts": datetime.now(UTC).isoformat(),
                }
                await _broadcast_collab(session_id, message)
            elif msg_type == "broadcast":
                data = dict(payload.get("data", {}))
                data.setdefault("session_id", session_id)
                data.setdefault("sender_id", user_id)
                await _broadcast_collab(session_id, {"type": "collab_event", "data": data})
            else:
                await websocket.send_json({"type": "error", "error": "unknown_type", "msg_type": msg_type})
    except Exception as e:
        logger.warning("generic.ws_collab_endpoint_disconnect", error=str(e))
    finally:
        conns = _collab_ws_connections.get(session_id)
        if conns:
            conns.discard(websocket)
            if not conns:
                _collab_ws_connections.pop(session_id, None)
        try:
            await websocket.close()
        except Exception as e:
            logger.warning("generic.ws_collab_endpoint_close", error=str(e))


async def _broadcast_collab(session_id: str, message: dict[str, Any]) -> None:
    conns = list(_collab_ws_connections.get(session_id, set()))
    for ws in conns:
        try:
            await ws.send_json(message)
        except Exception as e:
            logger.debug("generic.collab_ws_send_failed", session_id=session_id, error=str(e))

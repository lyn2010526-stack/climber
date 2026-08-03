"""WebSocket API endpoints."""

from __future__ import annotations

import json

import structlog
from fastapi import APIRouter, WebSocket

logger = structlog.get_logger()
from sqlalchemy import select

from app.core.auth import LOCAL_USER_ID
from app.storage import async_session
from app.storage.models_groups import AgentGroup

router = APIRouter()


@router.websocket("/ws/{session_id}")
async def ws_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    await websocket.send_json({"type": "connected", "session_id": session_id})
    try:
        while True:
            msg = await websocket.receive_text()
            await websocket.send_json({"type": "echo", "data": msg})
    except Exception as e:
        logger.warning("websocket.ws_endpoint_disconnect", error=str(e))
    finally:
        try:
            await websocket.close()
        except Exception as e:
            logger.warning("websocket.ws_endpoint_close", error=str(e))


@router.websocket("/ws/groups/{group_id}")
async def ws_group_endpoint(websocket: WebSocket, group_id: str):
    from app.core.group_ws_hub import group_ws_hub

    await websocket.accept()
    user_id = LOCAL_USER_ID

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
        logger.warning("websocket.ws_group_endpoint_disconnect", error=str(e))
    finally:
        await group_ws_hub.disconnect(group_id, websocket)
        try:
            await websocket.close()
        except Exception as e:
            logger.warning("websocket.ws_group_endpoint_close", error=str(e))

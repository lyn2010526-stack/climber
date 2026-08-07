"""WebSocket endpoints for real-time communication with heartbeat and reconnection support."""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
from typing import Any

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from starlette.websockets import WebSocketState

from app.config import settings
from app.core.auth import LOCAL_USER_ID
from app.core.group_ws_hub import group_ws_hub
from app.middleware.auth import authenticate_credentials
from app.storage import async_session
from app.storage.database import Agent, Session
from app.storage.models_groups import AgentGroup

logger = structlog.get_logger(__name__)

websocket_router = APIRouter()
router = websocket_router

_heartbeat_interval = 30

_session_states: dict[str, dict[str, Any]] = {}
_agent_states: dict[str, dict[str, Any]] = {}


async def _websocket_heartbeat(websocket: WebSocket, session_id: str) -> None:
    """Send periodic ping frames to keep connection alive."""
    try:
        while True:
            await asyncio.sleep(_heartbeat_interval)
            await websocket.send_json({"type": "ping", "timestamp": time.time()})
    except asyncio.CancelledError:
        return
    except Exception:
        return


async def _receive_with_timeout(websocket: WebSocket, timeout: float = 40.0) -> str | None:
    """Receive a message with timeout to detect stale connections."""
    try:
        return await asyncio.wait_for(websocket.receive_text(), timeout=timeout)
    except TimeoutError:
        return None
    except WebSocketDisconnect:
        raise
    except Exception:
        raise


async def _safe_close(websocket: WebSocket, log_key: str) -> None:
    """Safely close a WebSocket connection, logging any errors."""
    if websocket.application_state == WebSocketState.DISCONNECTED:
        return
    try:
        await websocket.close()
    except Exception as e:
        logger.warning(log_key, error=str(e))


async def _authenticate_websocket(
    websocket: WebSocket,
    resource_model: type | None = None,
    resource_id: str | None = None,
) -> str | None:
    """Authenticate a socket and authorize access to an existing resource."""
    if not settings.enable_auth:
        return LOCAL_USER_ID

    auth = await authenticate_credentials(
        websocket.headers,
        token=websocket.query_params.get("token"),
    )
    user_id = None
    if auth:
        user_id = auth.get("sub") or auth.get("owner")
    if not user_id:
        await websocket.close(code=4401)
        return None

    if resource_model is not None and resource_id is not None:
        async with async_session() as db:
            owner_id = (
                await db.execute(
                    select(resource_model.user_id).where(resource_model.id == resource_id)
                )
            ).scalar_one_or_none()
        if owner_id is not None and str(owner_id) != str(user_id):
            await websocket.close(code=4403)
            return None

    return str(user_id)


@websocket_router.websocket("/ws/{session_id}")
async def ws_endpoint(websocket: WebSocket, session_id: str) -> None:
    """Session-scoped WebSocket endpoint with heartbeat and reconnection support.

    Args:
        websocket: The WebSocket connection.
        session_id: The session identifier.
    """
    heartbeat_task: asyncio.Task | None = None
    try:
        user_id = await _authenticate_websocket(websocket, Session, session_id)
        if user_id is None:
            return
        await websocket.accept()

        state = _session_states.get(session_id, {"messages": [], "connected_at": time.time()})
        state["last_active"] = time.time()
        state["connected"] = True
        _session_states[session_id] = state

        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "reconnect": state.get("disconnect_count", 0) > 0,
        })

        heartbeat_task = asyncio.create_task(_websocket_heartbeat(websocket, session_id))

        while True:
            try:
                raw = await _receive_with_timeout(websocket)
                if raw is None:
                    await websocket.send_json({"type": "pong"})
                    continue

                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "error": "invalid_json"})
                    continue

                if payload.get("type") == "pong":
                    state["last_active"] = time.time()
                    continue

                if payload.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": time.time()})
                    continue

                state.setdefault("messages", []).append(payload)
                state["last_active"] = time.time()

                await websocket.send_json({"type": "echo", "data": payload, "session_id": session_id})

            except WebSocketDisconnect:
                raise
    except WebSocketDisconnect as e:
        logger.info("websocket.session_disconnect", session_id=session_id, code=e.code)
    except Exception as e:
        logger.warning("websocket.session_error", session_id=session_id, error=str(e))
    finally:
        if heartbeat_task and not heartbeat_task.done():
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task

        state = _session_states.get(session_id)
        if state:
            state["connected"] = False
            state["disconnect_count"] = state.get("disconnect_count", 0) + 1
            state["last_disconnect"] = time.time()

        await _safe_close(websocket, "ws_endpoint_close")


@websocket_router.websocket("/ws/groups/{group_id}")
async def ws_group_endpoint(websocket: WebSocket, group_id: str) -> None:
    """Group collaboration WebSocket endpoint with heartbeat and reconnection support.

    Args:
        websocket: The WebSocket connection.
        group_id: The group identifier.
    """
    heartbeat_task: asyncio.Task | None = None
    try:
        user_id = await _authenticate_websocket(websocket, AgentGroup, group_id)
        if user_id is None:
            return
        await websocket.accept()

        try:
            async with async_session() as db:
                group = (
                    await db.execute(select(AgentGroup).where(AgentGroup.id == group_id))
                ).scalar_one_or_none()
                if group is None:
                    await websocket.send_json({"type": "error", "error": "group_not_found"})
                    return
        except Exception as db_err:
            logger.warning("websocket.group_db_error", group_id=group_id, error=str(db_err))
            await websocket.send_json({"type": "error", "error": "database_error"})
            return

        await group_ws_hub.connect(group_id, websocket)

        heartbeat_task = asyncio.create_task(_websocket_heartbeat(websocket, f"group:{group_id}"))

        while True:
            try:
                raw = await _receive_with_timeout(websocket)
                if raw is None:
                    await websocket.send_json({"type": "pong"})
                    continue

                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "error": "invalid_json"})
                    continue

                if payload.get("type") == "pong":
                    continue

                if payload.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": time.time()})
                    continue

                if payload.get("type") == "message":
                    payload["sender_id"] = user_id

                await group_ws_hub.disconnect(group_id, websocket)
                try:
                    result = await group_ws_hub.handle_message(group_id, payload)
                finally:
                    await group_ws_hub.connect(group_id, websocket)
                await websocket.send_json({"type": "ack", "data": result})

            except WebSocketDisconnect:
                raise
    except WebSocketDisconnect as e:
        logger.info("websocket.group_disconnect", group_id=group_id, code=e.code)
    except Exception as e:
        logger.warning("websocket.group_error", group_id=group_id, error=str(e))
    finally:
        if heartbeat_task and not heartbeat_task.done():
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task

        await group_ws_hub.disconnect(group_id, websocket)
        await _safe_close(websocket, "ws_group_endpoint_close")


@websocket_router.websocket("/ws/agents/{agent_id}")
async def ws_agent_endpoint(websocket: WebSocket, agent_id: str) -> None:
    """Agent-specific WebSocket endpoint for direct agent communication.

    Args:
        websocket: The WebSocket connection.
        agent_id: The agent identifier.
    """
    heartbeat_task: asyncio.Task | None = None
    try:
        user_id = await _authenticate_websocket(websocket, Agent, agent_id)
        if user_id is None:
            return
        await websocket.accept()

        try:
            async with async_session() as db:
                agent = (
                    await db.execute(select(Agent).where(Agent.id == agent_id))
                ).scalar_one_or_none()
                if agent is None:
                    await websocket.send_json({"type": "error", "error": "agent_not_found"})
                    return
        except Exception as db_err:
            logger.warning("websocket.agent_db_error", agent_id=agent_id, error=str(db_err))
            await websocket.send_json({"type": "error", "error": "database_error"})
            return

        state = _agent_states.get(agent_id, {"messages": [], "connected_at": time.time()})
        state["last_active"] = time.time()
        state["connected"] = True
        _agent_states[agent_id] = state

        await websocket.send_json({
            "type": "connected",
            "agent_id": agent_id,
            "agent_name": agent.name,
            "reconnect": state.get("disconnect_count", 0) > 0,
        })

        heartbeat_task = asyncio.create_task(_websocket_heartbeat(websocket, f"agent:{agent_id}"))

        while True:
            try:
                raw = await _receive_with_timeout(websocket)
                if raw is None:
                    await websocket.send_json({"type": "pong"})
                    continue

                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "error": "invalid_json"})
                    continue

                if payload.get("type") == "pong":
                    state["last_active"] = time.time()
                    continue

                if payload.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": time.time()})
                    continue

                state.setdefault("messages", []).append(payload)
                state["last_active"] = time.time()

                await websocket.send_json({
                    "type": "agent_message",
                    "agent_id": agent_id,
                    "data": payload,
                })

            except WebSocketDisconnect:
                raise
    except WebSocketDisconnect as e:
        logger.info("websocket.agent_disconnect", agent_id=agent_id, code=e.code)
    except Exception as e:
        logger.warning("websocket.agent_error", agent_id=agent_id, error=str(e))
    finally:
        if heartbeat_task and not heartbeat_task.done():
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task

        state = _agent_states.get(agent_id)
        if state:
            state["connected"] = False
            state["disconnect_count"] = state.get("disconnect_count", 0) + 1
            state["last_disconnect"] = time.time()

        await _safe_close(websocket, "ws_agent_endpoint_close")

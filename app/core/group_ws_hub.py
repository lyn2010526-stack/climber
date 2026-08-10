"""Group collaboration WebSocket hub."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any

import structlog

from app.storage import async_session
from app.storage.models_groups import AgentGroup, AgentGroupMember, AgentGroupMessage, AgentGroupTask
from sqlalchemy import select

logger = structlog.get_logger()

# Active WebSocket connections per group
_group_connections: dict[str, set[Any]] = defaultdict(set)

# Supported event types for documentation and validation
SUPPORTED_EVENT_TYPES = {
    # Core events
    "message",
    "member_update",
    "task_update",
    # Task lifecycle
    "task_started",
    "task_running",
    "task_paused",
    "task_completed",
    "task_partial",
    "task_failed",
    "task_stopped",
    # Agent execution
    "worker_start",
    "worker_done",
    "worker_error",
    "worker_tool_call",
    "reviewer_start",
    "reviewer_done",
    "reviewer_error",
    "manager_start",
    "manager_done",
    "manager_assign",
    # Progress
    "progress_update",
    "step_complete",
    "task_checkpoint",
    # Callbacks
    "step_callback",
    "task_callback",
    # Memory
    "memory_injected",
    "memory_stored",
    # Guardrails
    "guardrail_check",
    "guardrail_passed",
    "guardrail_failed",
    "guardrail_retry",
    # Human-in-the-loop
    "human_review_needed",
    "human_review_approved",
    "human_review_rejected",
    # Checkpoint
    "checkpoint_created",
    "checkpoint_restored",
    # Process type events
    "hierarchical_plan",
    "hierarchical_delegate",
    "hierarchical_validate",
    "group_chat_turn",
    "group_chat_consensus",
    # System
    "system_message",
    "error",
    "typing",
}


class GroupWebSocketHub:
    """Minimal in-process hub for group collaboration."""

    async def connect(self, group_id: str, websocket: Any) -> None:
        _group_connections[group_id].add(websocket)
        logger.info("group_ws_connected", group_id=group_id, total=len(_group_connections[group_id]))

    async def disconnect(self, group_id: str, websocket: Any) -> None:
        conns = _group_connections.get(group_id)
        if conns and websocket in conns:
            conns.remove(websocket)
        logger.info("group_ws_disconnected", group_id=group_id, total=len(_group_connections.get(group_id, [])))

    async def broadcast(self, group_id: str, message: dict[str, Any]) -> None:
        event_type = message.get("type", "")
        if event_type not in SUPPORTED_EVENT_TYPES:
            logger.warning("unsupported_ws_event_type", event_type=event_type)
        conns = _group_connections.get(group_id, set())
        dead: list[Any] = []
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            conns.discard(ws)

    async def handle_message(self, group_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        kind = payload.get("type")
        if kind == "message":
            return await self._save_group_message(group_id, payload)
        if kind == "member_update":
            return await self._update_member_status(group_id, payload)
        if kind == "task_update":
            return await self._update_task_status(group_id, payload)
        if kind == "human_review_response":
            return await self._handle_human_review(group_id, payload)
        return {"ok": False, "error": "unknown_type"}

    async def _save_group_message(self, group_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with async_session() as db:
            msg = AgentGroupMessage(
                group_id=group_id,
                sender_id=payload.get("sender_id", ""),
                sender_name=payload.get("sender_name", "Anonymous"),
                content=payload.get("content", ""),
                message_type=payload.get("message_type", "text"),
                metadata=payload.get("metadata", {}),
            )
            db.add(msg)
            await db.commit()
            await db.refresh(msg)
            result = {
                "ok": True,
                "id": msg.id,
                "created_at": msg.created_at.isoformat() if msg.created_at else "",
            }
        await self.broadcast(group_id, {"type": "message", "data": result})
        return result

    async def _update_member_status(self, group_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        member_id = payload.get("member_id")
        if not member_id:
            return {"ok": False, "error": "member_id required"}
        async with async_session() as db:
            member = (
                await db.execute(
                    select(AgentGroupMember).where(
                        AgentGroupMember.id == member_id,
                        AgentGroupMember.group_id == group_id,
                    )
                )
            ).scalar_one_or_none()
            if member is None:
                return {"ok": False, "error": "member not found"}
            if "status" in payload:
                member.status = payload["status"]
            if "current_task_id" in payload:
                member.current_task_id = payload["current_task_id"]
            await db.commit()
            return {"ok": True, "id": member_id}

    async def _update_task_status(self, group_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        task_id = payload.get("task_id")
        if not task_id:
            return {"ok": False, "error": "task_id required"}
        async with async_session() as db:
            task = (
                await db.execute(
                    select(AgentGroupTask).where(
                        AgentGroupTask.id == task_id,
                        AgentGroupTask.group_id == group_id,
                    )
                )
            ).scalar_one_or_none()
            if task is None:
                return {"ok": False, "error": "task not found"}
            if "status" in payload:
                task.status = payload["status"]
            if "worker_id" in payload:
                task.worker_id = payload["worker_id"]
            if "current_round" in payload:
                task.current_round = int(payload["current_round"])
            await db.commit()
            await self.broadcast(group_id, {"type": "task_update", "data": {"id": task.id, "status": task.status}})
            return {"ok": True, "id": task_id}

    async def _handle_human_review(self, group_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle human review response (approve/reject)."""
        task_id = payload.get("task_id")
        decision = payload.get("decision")  # "approved" or "rejected"
        comment = payload.get("comment", "")
        if not task_id or not decision:
            return {"ok": False, "error": "task_id and decision required"}
        async with async_session() as db:
            task = (
                await db.execute(
                    select(AgentGroupTask).where(
                        AgentGroupTask.id == task_id,
                        AgentGroupTask.group_id == group_id,
                    )
                )
            ).scalar_one_or_none()
            if task is None:
                return {"ok": False, "error": "task not found"}
            task.human_review_status = decision
            task.human_review_comment = comment
            if decision == "approved":
                task.status = "running"
            elif decision == "rejected":
                task.status = "failed"
            await db.commit()
        event_type = "human_review_approved" if decision == "approved" else "human_review_rejected"
        await self.broadcast(group_id, {
            "type": event_type,
            "data": {"task_id": task_id, "comment": comment},
        })
        return {"ok": True, "id": task_id, "decision": decision}


group_ws_hub = GroupWebSocketHub()

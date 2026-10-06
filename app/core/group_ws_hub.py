"""Group collaboration WebSocket hub.

Broadcasts group collaboration events with a unified event protocol. Legacy
event names keep flowing untouched so existing frontend listeners stay
compatible; every legacy frame is additionally mirrored as one of the six
canonical protocol events (status / content_delta / tool_result /
task_update / message_complete / error) whose payload carries a type label.

Client disconnects never stop running tasks: the hub only detaches the
socket, and reconnecting clients can pull authoritative state through the
synchronous snapshot query functions.
"""

from __future__ import annotations

from collections import OrderedDict, defaultdict, deque
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select

from app.storage import async_session
from app.storage.models_groups import AgentGroupMember, AgentGroupMessage, AgentGroupTask

logger = structlog.get_logger()

# Active WebSocket connections per group
_group_connections: dict[str, set[Any]] = defaultdict(set)

# Unified (canonical) event protocol version and the six canonical event
# types every consumer can subscribe to.
EVENT_PROTOCOL_VERSION = 1

CANONICAL_EVENT_TYPES = {
    "status",
    "content_delta",
    "tool_result",
    "task_update",
    "message_complete",
    "error",
}

# Mapping from legacy event names to their canonical protocol event. Entries
# whose canonical type equals the legacy name are identity mappings (the
# legacy frame already conforms, so no mirror frame is emitted).
LEGACY_EVENT_MAP: dict[str, str] = {
    # Chat messages finalize into complete messages
    "message": "message_complete",
    "group_chat_turn": "message_complete",
    "worker_done": "message_complete",
    "reviewer_done": "message_complete",
    # Agent / step runtime state
    "member_update": "status",
    "worker_start": "status",
    "worker_error": "status",
    "reviewer_start": "status",
    "reviewer_error": "status",
    "manager_start": "status",
    "manager_done": "status",
    "manager_assign": "status",
    "progress_update": "status",
    "step_complete": "status",
    "step_callback": "status",
    "task_callback": "status",
    "task_handoff": "status",
    "dag_level_start": "status",
    "hierarchical_plan": "status",
    "hierarchical_delegate": "status",
    "hierarchical_delegate_done": "status",
    "hierarchical_validate": "status",
    "group_chat_consensus": "status",
    "memory_injected": "status",
    "memory_stored": "status",
    "guardrail_check": "status",
    "guardrail_passed": "status",
    "guardrail_failed": "status",
    "guardrail_retry": "status",
    "human_review_needed": "status",
    "human_review_approved": "status",
    "human_review_rejected": "status",
    "system_message": "status",
    "typing": "status",
    "progress_warning": "status",
    "progress_snapshot": "status",
    # Tool activity
    "worker_tool_call": "tool_result",
    # Task lifecycle
    "task_started": "task_update",
    "task_running": "task_update",
    "task_paused": "task_update",
    "task_completed": "task_update",
    "task_partial": "task_update",
    "task_stopped": "task_update",
    "task_failed": "error",
    "task_checkpoint": "task_update",
    "checkpoint_created": "task_update",
    "checkpoint_restored": "task_update",
    "tree_node_added": "task_update",
    "tree_node_updated": "task_update",
    # Identity mappings (legacy frame already conforms to the protocol)
    "status": "status",
    "content_delta": "content_delta",
    "tool_result": "tool_result",
    "task_update": "task_update",
    "message_complete": "message_complete",
    "error": "error",
}

# Supported event types for documentation and validation
SUPPORTED_EVENT_TYPES = {
    *LEGACY_EVENT_MAP.keys(),
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
    "hierarchical_delegate_done",
    "hierarchical_validate",
    "group_chat_turn",
    "group_chat_consensus",
    "dag_level_start",
    "task_handoff",
    # Unified protocol
    *CANONICAL_EVENT_TYPES,
    "tree_node_added",
    "tree_node_updated",
    "progress_warning",
    "progress_snapshot",
    # System
    "system_message",
    "error",
    "typing",
}

# Snapshot support: recent events per group so reconnecting clients can
# pull state instead of replaying from scratch. Client disconnects never
# stop tasks; the log keeps recording while tasks continue.
_MAX_TRACKED_GROUPS = 512
_MAX_GROUP_EVENTS = 200
_group_event_log: OrderedDict[str, deque] = OrderedDict()


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _record_event(group_id: str, message: dict[str, Any]) -> None:
    """Append a frame to the per-group snapshot log with bounded size."""
    log = _group_event_log.get(group_id)
    if log is None:
        if len(_group_event_log) >= _MAX_TRACKED_GROUPS:
            _group_event_log.popitem(last=False)
        log = deque(maxlen=_MAX_GROUP_EVENTS)
        _group_event_log[group_id] = log
    log.append({"at": _utc_now_iso(), "message": message})


def get_group_event_log(group_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Return the most recent broadcast frames for a group (sync query)."""
    log = _group_event_log.get(group_id)
    if not log or limit <= 0:
        return []
    return list(log)[-limit:]


def get_group_state_snapshot(group_id: str) -> dict[str, Any]:
    """Synchronous state snapshot for reconnecting clients.

    Clients may disconnect at any time; running tasks continue in the
    background. A reconnecting client pulls this snapshot (recent frames,
    live sub-agent task tree and progress trackers) to catch up.
    """
    from app.core.collaboration.progress import (
        get_progress_snapshots,
        get_task_tree_snapshot,
    )

    return {
        "group_id": group_id,
        "generated_at": _utc_now_iso(),
        "protocol_version": EVENT_PROTOCOL_VERSION,
        "connected_clients": len(_group_connections.get(group_id, set())),
        "recent_events": get_group_event_log(group_id),
        "task_tree": get_task_tree_snapshot(group_id),
        "progress": get_progress_snapshots(group_id),
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
        """Broadcast a legacy event frame, then mirror it canonically.

        The original frame is sent unchanged so existing listeners on
        legacy event names keep working. When the legacy event maps to a
        canonical protocol event, a second frame is emitted whose payload
        carries the type label under ``event``.
        """
        event_type = message.get("type", "")
        if event_type not in SUPPORTED_EVENT_TYPES:
            logger.warning("unsupported_ws_event_type", event_type=event_type)
        await self._send(group_id, message)
        _record_event(group_id, message)
        canonical = LEGACY_EVENT_MAP.get(event_type)
        if canonical and canonical != event_type:
            await self.broadcast_canonical(
                group_id,
                canonical,
                dict(message.get("data") or {}),
                kind=event_type,
            )

    async def broadcast_canonical(
        self,
        group_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        kind: str | None = None,
        correlation_id: str | None = None,
    ) -> bool:
        """Broadcast a single canonical protocol frame with a type label.

        Args:
            group_id: The group ID to broadcast to.
            event_type: One of the six canonical event types.
            payload: The event payload.
            kind: Optional finer-grained label stored in ``payload["event"]``.
            correlation_id: Optional correlation ID hoisted into the payload.

        Returns:
            True when the frame was sent, False for an unknown event type.
        """
        if event_type not in CANONICAL_EVENT_TYPES:
            logger.warning("invalid_canonical_event_type", event_type=event_type)
            return False
        data = dict(payload or {})
        data.setdefault("event", kind or event_type)
        data.setdefault("protocol_version", EVENT_PROTOCOL_VERSION)
        if correlation_id:
            data.setdefault("correlation_id", correlation_id)
        frame = {"type": event_type, "data": data}
        await self._send(group_id, frame)
        _record_event(group_id, frame)
        return True

    async def _send(self, group_id: str, message: dict[str, Any]) -> None:
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

"""MCP Plugin: Inter-Agent Communication — sub-agent messaging.

Standardized message passing, conflict resolution, and result merging
for hierarchical multi-agent systems.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MessageType(str, Enum):
    TASK_ASSIGN = "task_assign"
    RESULT_REPORT = "result_report"
    HELP_REQUEST = "help_request"
    CONFLICT_REPORT = "conflict_report"
    STATUS_UPDATE = "status_update"


class MessagePriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AgentMessage:
    id: str
    sender: str
    recipient: str
    type: MessageType
    content: dict[str, Any]
    priority: MessagePriority
    timestamp: float
    replied_to: str | None = None


@dataclass
class ConflictReport:
    agents: list[str]
    description: str
    proposed_resolution: str


class InterAgentCommunication:
    """Message bus for sub-agent coordination."""

    def __init__(self, storage_path: str = "data/agent_messages.json"):
        self._storage_path = storage_path
        self._messages: list[AgentMessage] = []
        self._agent_inboxes: dict[str, list[str]] = {}
        self._load()

    def send(
        self,
        sender: str,
        recipient: str,
        msg_type: MessageType,
        content: dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> AgentMessage:
        msg = AgentMessage(
            id=str(uuid.uuid4())[:8],
            sender=sender,
            recipient=recipient,
            type=msg_type,
            content=content,
            priority=priority,
            timestamp=time.time(),
        )
        self._messages.append(msg)
        self._agent_inboxes.setdefault(recipient, []).append(msg.id)
        self._save()
        return msg

    def broadcast(
        self,
        sender: str,
        recipients: list[str],
        msg_type: MessageType,
        content: dict[str, Any],
    ) -> list[AgentMessage]:
        messages = []
        for recipient in recipients:
            msg = self.send(sender, recipient, msg_type, content)
            messages.append(msg)
        return messages

    def receive(self, agent_id: str, limit: int = 10) -> list[AgentMessage]:
        """Get messages for an agent, oldest first."""
        msg_ids = self._agent_inboxes.get(agent_id, [])
        messages = [
            m for m in self._messages if m.id in msg_ids
        ]
        messages.sort(key=lambda m: m.timestamp)
        return messages[:limit]

    def get_unread_count(self, agent_id: str) -> int:
        return len(self._agent_inboxes.get(agent_id, []))

    def report_conflict(
        self,
        reporter: str,
        agents_involved: list[str],
        description: str,
    ) -> ConflictReport:
        """Report a conflict between agents."""
        resolution = self._resolve_conflict(agents_involved, description)
        self.send(
            reporter,
            "orchestrator",
            MessageType.CONFLICT_REPORT,
            {
                "agents": agents_involved,
                "description": description,
                "resolution": resolution,
            },
            priority=MessagePriority.HIGH,
        )
        return ConflictReport(
            agents=agents_involved,
            description=description,
            proposed_resolution=resolution,
        )

    def _resolve_conflict(self, agents: list[str], description: str) -> str:
        """Propose a resolution for the conflict."""
        desc_lower = description.lower()

        if "resource" in desc_lower or "lock" in desc_lower:
            return "Implement priority-based resource allocation: earlier task gets priority"

        if "overwrite" in desc_lower or "conflict" in desc_lower:
            return "Merge changes: take non-conflicting parts from both, flag conflicts for review"

        if "scope" in desc_lower or "overlap" in desc_lower:
            return "Split scope: assign distinct sub-tasks to each agent"

        return "Escalate to orchestrator for manual resolution"

    def merge_results(
        self,
        agent_ids: list[str],
        merge_strategy: str = "concatenate",
    ) -> dict[str, Any]:
        """Merge results from multiple agents."""
        all_results = []
        for agent_id in agent_ids:
            msgs = self.receive(agent_id)
            for msg in msgs:
                if msg.type == MessageType.RESULT_REPORT:
                    all_results.append(msg.content)

        if merge_strategy == "concatenate":
            return {
                "merged": True,
                "strategy": "concatenate",
                "results": all_results,
                "count": len(all_results),
            }
        elif merge_strategy == "vote":
            return {
                "merged": True,
                "strategy": "vote",
                "results": all_results,
                "consensus": all_results[0] if all_results else None,
            }
        else:
            return {"merged": False, "error": f"Unknown strategy: {merge_strategy}"}

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "agent_send",
                "description": "Send a message to another agent",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sender": {"type": "string"},
                        "recipient": {"type": "string"},
                        "msg_type": {
                            "type": "string",
                            "enum": ["task_assign", "result_report", "help_request", "conflict_report", "status_update"],
                        },
                        "content": {"type": "object"},
                    },
                    "required": ["sender", "recipient", "msg_type", "content"],
                },
            },
            {
                "name": "agent_receive",
                "description": "Receive messages for an agent",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                    "required": ["agent_id"],
                },
            },
            {
                "name": "agent_report_conflict",
                "description": "Report a conflict between agents",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reporter": {"type": "string"},
                        "agents_involved": {"type": "array", "items": {"type": "string"}},
                        "description": {"type": "string"},
                    },
                    "required": ["reporter", "agents_involved", "description"],
                },
            },
        ]

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._storage_path), exist_ok=True)
        data = [
            {
                "id": m.id,
                "sender": m.sender,
                "recipient": m.recipient,
                "type": m.type.value,
                "content": m.content,
                "priority": m.priority.value,
                "timestamp": m.timestamp,
            }
            for m in self._messages[-100:]  # Keep last 100
        ]
        with open(self._storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self) -> None:
        if not os.path.exists(self._storage_path):
            return
        try:
            with open(self._storage_path) as f:
                data = json.load(f)
            for m in data:
                msg = AgentMessage(
                    id=m["id"],
                    sender=m["sender"],
                    recipient=m["recipient"],
                    type=MessageType(m["type"]),
                    content=m["content"],
                    priority=MessagePriority(m.get("priority", "normal")),
                    timestamp=m.get("timestamp", 0),
                )
                self._messages.append(msg)
                self._agent_inboxes.setdefault(msg.recipient, []).append(msg.id)
        except (json.JSONDecodeError, KeyError):
            pass

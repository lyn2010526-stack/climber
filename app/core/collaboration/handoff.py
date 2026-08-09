"""Task Handoff Management.

Provides task handoff between agents with context transfer,
capability matching, and audit trail.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HandoffStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class HandoffRequest:
    """Represents a handoff request between agents."""

    task_id: str = ""
    from_agent_id: str = ""
    to_agent_id: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    requested_at: float = field(default_factory=time.time)
    status: HandoffStatus = HandoffStatus.PENDING
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    reason: str = ""
    audit_log: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "from_agent_id": self.from_agent_id,
            "to_agent_id": self.to_agent_id,
            "context": self.context,
            "priority": self.priority,
            "requested_at": self.requested_at,
            "status": self.status.value,
            "reason": self.reason,
        }


@dataclass
class AgentCapability:
    """Agent capability descriptor for matching."""

    agent_id: str
    capabilities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class HandoffManager:
    """Manages task handoffs between agents."""

    def __init__(self) -> None:
        self._handoffs: dict[str, HandoffRequest] = {}
        self._agent_capabilities: dict[str, AgentCapability] = {}
        self._audit_trail: list[dict[str, Any]] = []

    def register_agent_capability(self, agent: AgentCapability) -> None:
        """Register an agent's capabilities for matching."""
        self._agent_capabilities[agent.agent_id] = agent

    def request_handoff(
        self,
        task_id: str,
        from_agent_id: str,
        to_agent_id: str,
        context: dict[str, Any] | None = None,
        priority: int = 0,
    ) -> HandoffRequest:
        """Create a new handoff request."""
        handoff = HandoffRequest(
            task_id=task_id,
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            context=context or {},
            priority=priority,
        )
        handoff.audit_log.append({
            "action": "created",
            "timestamp": time.time(),
            "agent_id": from_agent_id,
        })
        self._handoffs[handoff.id] = handoff
        self._audit_trail.append({
            "handoff_id": handoff.id,
            "action": "created",
            "task_id": task_id,
            "from_agent_id": from_agent_id,
            "to_agent_id": to_agent_id,
            "timestamp": time.time(),
        })
        return handoff

    def accept_handoff(self, handoff_id: str) -> HandoffRequest | None:
        """Accept a pending handoff request."""
        handoff = self._handoffs.get(handoff_id)
        if not handoff or handoff.status != HandoffStatus.PENDING:
            return None
        handoff.status = HandoffStatus.ACCEPTED
        handoff.audit_log.append({
            "action": "accepted",
            "timestamp": time.time(),
            "agent_id": handoff.to_agent_id,
        })
        self._audit_trail.append({
            "handoff_id": handoff_id,
            "action": "accepted",
            "timestamp": time.time(),
        })
        return handoff

    def reject_handoff(self, handoff_id: str, reason: str = "") -> HandoffRequest | None:
        """Reject a pending handoff request."""
        handoff = self._handoffs.get(handoff_id)
        if not handoff or handoff.status != HandoffStatus.PENDING:
            return None
        handoff.status = HandoffStatus.REJECTED
        handoff.reason = reason
        handoff.audit_log.append({
            "action": "rejected",
            "timestamp": time.time(),
            "agent_id": handoff.to_agent_id,
            "reason": reason,
        })
        self._audit_trail.append({
            "handoff_id": handoff_id,
            "action": "rejected",
            "reason": reason,
            "timestamp": time.time(),
        })
        return handoff

    def get_pending_handoffs(self, agent_id: str | None = None) -> list[HandoffRequest]:
        """Get pending handoffs, optionally filtered by target agent."""
        pending = [
            h for h in self._handoffs.values()
            if h.status == HandoffStatus.PENDING
        ]
        if agent_id:
            pending = [h for h in pending if h.to_agent_id == agent_id]
        return pending

    def get_handoff(self, handoff_id: str) -> HandoffRequest | None:
        """Get a handoff by ID."""
        return self._handoffs.get(handoff_id)

    def find_capable_agent(self, required_capabilities: list[str]) -> str | None:
        """Find an agent that has all required capabilities."""
        for agent in self._agent_capabilities.values():
            if all(cap in agent.capabilities for cap in required_capabilities):
                return agent.agent_id
        return None

    def auto_handoff(
        self,
        task_id: str,
        from_agent_id: str,
        required_capabilities: list[str],
        context: dict[str, Any] | None = None,
        priority: int = 0,
    ) -> HandoffRequest | None:
        """Automatically find a capable agent and create handoff."""
        target_id = self.find_capable_agent(required_capabilities)
        if not target_id:
            return None
        return self.request_handoff(
            task_id=task_id,
            from_agent_id=from_agent_id,
            to_agent_id=target_id,
            context=context,
            priority=priority,
        )

    def get_audit_trail(self, handoff_id: str | None = None) -> list[dict[str, Any]]:
        """Get audit trail, optionally filtered by handoff ID."""
        if handoff_id:
            return [e for e in self._audit_trail if e.get("handoff_id") == handoff_id]
        return list(self._audit_trail)

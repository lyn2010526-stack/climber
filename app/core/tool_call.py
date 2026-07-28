"""ToolCall lifecycle state machine.

"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ToolCallStatus(Enum):
    PENDING = "pending"
    ASKING = "asking"                   # waiting for user approval
    ALLOWED = "allowed"
    EXECUTING = "executing"
    FINISHED = "finished"
    ERROR = "error"
    INTERRUPTED = "interrupted"


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
    status: ToolCallStatus = ToolCallStatus.PENDING
    result: str | None = None
    error: str | None = None
    duration_ms: float | None = None
    user_decision: str | None = None  # approve / deny / timeout
    metadata: dict[str, Any] = field(default_factory=dict)


class ToolCallManager:
    """Manage tool call lifecycle."""

    def __init__(self):
        self._calls: dict[str, ToolCall] = {}
        self._listeners: dict[str, list[Callable]] = {}

    def create(self, name: str, arguments: dict[str, Any]) -> ToolCall:
        """Create a new tool call."""
        import uuid
        call = ToolCall(id=str(uuid.uuid4()), name=name, arguments=arguments)
        self._calls[call.id] = call
        return call

    def get(self, call_id: str) -> ToolCall | None:
        return self._calls.get(call_id)

    def transition(self, call_id: str, new_status: ToolCallStatus, **kwargs: Any) -> bool:
        """Transition a tool call to a new status."""
        call = self._calls.get(call_id)
        if not call:
            return False
        old_status = call.status
        call.status = new_status
        for key, value in kwargs.items():
            setattr(call, key, value)
        logger.info("tool_call_transition", call_id=call_id, old=old_status.value, new=new_status.value)
        return True

    def list_pending(self) -> list[ToolCall]:
        return [c for c in self._calls.values() if c.status in (ToolCallStatus.PENDING, ToolCallStatus.ASKING)]

    def list_by_status(self, status: ToolCallStatus) -> list[ToolCall]:
        return [c for c in self._calls.values() if c.status == status]


tool_call_manager = ToolCallManager()

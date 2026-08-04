"""Standardized agent-to-agent message protocol.

Typed messages for structured communication between agents.
Replaces free-text communication that causes ambiguity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from datetime import datetime, timezone


class MessageType(str, Enum):
    # Task lifecycle
    TASK_ASSIGNED = "task_assigned"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"

    # Analysis and planning
    ANALYSIS = "analysis"
    PLAN = "plan"
    REQUIREMENTS = "requirements"

    # Implementation
    CODE_CHANGE = "code_change"
    CODE_REVIEW = "code_review"
    TEST_RESULT = "test_result"

    # Coordination
    APPROVAL = "approval"
    REJECTION = "rejection"
    REVISION_REQUEST = "revision_request"
    ESCALATION = "escalation"

    # Status
    PROGRESS = "progress"
    BLOCKED = "blocked"
    QUESTION = "question"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Confidence(float, Enum):
    LOW = 0.3
    MEDIUM = 0.6
    HIGH = 0.9
    CERTAIN = 1.0


@dataclass
class FileChange:
    """Represents a single file modification."""
    file_path: str
    change_type: str  # "create", "modify", "delete"
    description: str
    line_start: int | None = None
    line_end: int | None = None


@dataclass
class TestConclusion:
    """Test result summary."""
    passed: bool
    total_tests: int
    failed_tests: int
    coverage: float | None = None
    failures: list[str] = field(default_factory=list)


@dataclass
class AgentMessage:
    """Standardized message between agents."""
    type: MessageType
    sender: str
    content: str

    # Structured data
    priority: Priority = Priority.MEDIUM
    confidence: float = Confidence.MEDIUM

    # Optional structured payloads
    file_changes: list[FileChange] = field(default_factory=list)
    test_conclusion: TestConclusion | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    references: list[str] = field(default_factory=list)  # message IDs this responds to

    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    message_id: str = ""
    session_id: str = ""
    iteration: int = 0

    def __post_init__(self):
        if not self.message_id:
            import uuid
            self.message_id = str(uuid.uuid4())[:12]

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result = {
            "type": self.type.value,
            "sender": self.sender,
            "content": self.content,
            "priority": self.priority.value,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "message_id": self.message_id,
            "session_id": self.session_id,
            "iteration": self.iteration,
            "metrics": self.metrics,
            "references": self.references,
        }
        if self.file_changes:
            result["file_changes"] = [
                {
                    "file_path": fc.file_path,
                    "change_type": fc.change_type,
                    "description": fc.description,
                }
                for fc in self.file_changes
            ]
        if self.test_conclusion:
            result["test_conclusion"] = {
                "passed": self.test_conclusion.passed,
                "total_tests": self.test_conclusion.total_tests,
                "failed_tests": self.test_conclusion.failed_tests,
            }
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "AgentMessage":
        """Create from dictionary."""
        msg = cls(
            type=MessageType(data["type"]),
            sender=data["sender"],
            content=data["content"],
            priority=Priority(data.get("priority", "medium")),
            confidence=data.get("confidence", 0.6),
            session_id=data.get("session_id", ""),
            iteration=data.get("iteration", 0),
        )
        msg.message_id = data.get("message_id", msg.message_id)
        msg.timestamp = data.get("timestamp", msg.timestamp)
        return msg


class MessageBus:
    """In-memory message bus for agent communication."""

    def __init__(self):
        self._messages: list[AgentMessage] = []
        self._subscribers: dict[MessageType, list] = {}

    def publish(self, message: AgentMessage):
        """Publish a message to the bus."""
        self._messages.append(message)
        # Notify subscribers
        for handler in self._subscribers.get(message.type, []):
            handler(message)

    def subscribe(self, msg_type: MessageType, handler):
        """Subscribe to a message type."""
        self._subscribers.setdefault(msg_type, []).append(handler)

    def get_history(self, session_id: str | None = None, limit: int = 100) -> list[AgentMessage]:
        """Get message history."""
        messages = self._messages
        if session_id:
            messages = [m for m in messages if m.session_id == session_id]
        return messages[-limit:]

    def get_last(self, sender: str | None = None, msg_type: MessageType | None = None) -> AgentMessage | None:
        """Get last matching message."""
        for msg in reversed(self._messages):
            if sender and msg.sender != sender:
                continue
            if msg_type and msg.type != msg_type:
                continue
            return msg
        return None

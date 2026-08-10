"""Agent communication protocol.

"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Attachment:
    tool_name: str
    arguments: dict[str, Any]
    result: str
    error: str | None = None
    duration_ms: float = 0.0


@dataclass
class AgentMessage:
    id: str
    sender: str
    receiver: str | None
    content: str
    role: str = "assistant"
    attachments: list[Attachment] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    reply_to: str | None = None
    channel: str | None = None  # broadcast channel

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "role": self.role,
            "attachments": [
                {
                    "tool_name": a.tool_name,
                    "arguments": a.arguments,
                    "result": a.result,
                    "error": a.error,
                    "duration_ms": a.duration_ms,
                }
                for a in self.attachments
            ],
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "reply_to": self.reply_to,
            "channel": self.channel,
        }


class AgentMessageBus:
    """Message bus for inter-agent communication."""

    def __init__(self):
        self._messages: dict[str, list[AgentMessage]] = {}
        self._subscribers: dict[str, list[Callable]] = {}

    def send(self, message: AgentMessage) -> None:
        receiver = message.receiver
        if receiver:
            if receiver not in self._messages:
                self._messages[receiver] = []
            self._messages[receiver].append(message)
        else:
            # Broadcast
            for key in self._messages:
                self._messages[key].append(message)
        logger.debug("message_sent", message_id=message.id, sender=message.sender, receiver=receiver)

    def receive(self, agent_id: str, limit: int = 50) -> list[AgentMessage]:
        messages = self._messages.get(agent_id, [])
        self._messages[agent_id] = messages[limit:]
        return messages[-limit:]

    def peek(self, agent_id: str, limit: int = 50) -> list[AgentMessage]:
        messages = self._messages.get(agent_id, [])
        return messages[-limit:]


agent_message_bus = AgentMessageBus()

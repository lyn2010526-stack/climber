"""Agent event types and data classes."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class AgentEventType(StrEnum):
    TEXT = "text"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    DONE = "done"
    THINKING = "thinking"


@dataclass
class AgentEvent:
    type: AgentEventType
    data: dict[str, Any] = field(default_factory=dict)


class MessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ChatResult:
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tokens_used: int = 0


@dataclass
class ContextConfig:
    max_tokens: int = 8192
    max_tool_calls: int = 20
    system_prompt: str = ""
    compression_enabled: bool = True


class CompressionStrategy(StrEnum):
    """Context compression strategy."""
    SUMMARIZE = "summarize"
    TRUNCATE = "truncate"
    DROP_OLDEST = "drop_oldest"
    NONE = "none"


@dataclass
class CheckpointData:
    """Session checkpoint data."""
    session_id: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    version: int = 0


class SessionStatus(StrEnum):
    """Agent session status."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

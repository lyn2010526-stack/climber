"""Core types and base classes for the agent engine."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class CompressionStrategy(str, Enum):
    TRUNCATE = "truncate"
    SLIDING = "sliding"
    SUMMARIZE = "summarize"


class SessionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class AgentEventType(str, Enum):
    TEXT = "text"
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    DONE = "done"
    ERROR = "error"
    CHECKPOINT = "checkpoint"
    CONTEXT_COMPRESSION = "context_compression"
    MODEL_FALLBACK = "model_fallback"
    SUB_AGENT_START = "sub_agent_start"
    SUB_AGENT_END = "sub_agent_end"
    PROGRESS = "progress"


class FallbackStrategy(str, Enum):
    NEXT_MODEL = "next_model"
    CHEAPER_MODEL = "cheaper_model"
    RETRY = "retry"


@dataclass
class ChatResult:
    content: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    finish_reason: str | None = None
    tokens_used: int = 0


@dataclass
class AgentEvent:
    type: AgentEventType
    data: dict[str, Any] = field(default_factory=dict)

    def to_sse(self) -> str:
        payload = json.dumps(self.data)
        return f"event: {self.type.value}\ndata: {payload}\n\n"


@dataclass
class ModelRoute:
    provider: str
    model_id: str
    api_key: str
    priority: int = 0
    max_retries: int = 2
    base_url: str | None = None
    fallback_strategy: FallbackStrategy = FallbackStrategy.NEXT_MODEL


@dataclass
class SubAgentTask:
    task_id: str
    description: str
    provider: str
    model_id: str
    api_key: str
    base_url: str | None = None
    system_prompt: str = ""
    tools: list[str] = field(default_factory=list)


@dataclass
class ContextConfig:
    max_tokens: int = 4096
    compression_strategy: CompressionStrategy = CompressionStrategy.TRUNCATE
    keep_recent_messages: int = 4
    summarize_threshold: float = 0.8


from app.core.checkpoint import CheckpointData

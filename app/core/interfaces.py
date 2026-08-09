"""Core abstractions and interfaces for Climber.

This module defines the contracts that all major subsystems must implement,
enabling dependency injection and testability.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import structlog

# ── Events ──

class Event:
    type: str
    data: dict[str, Any]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[Event], None]]] = {}

    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)

    async def publish(self, event: Event) -> None:
        handlers = self._subscribers.get(event.type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as exc:
                logger = structlog.get_logger()
                logger.warning("event_handler_failed", event=event.type, error=str(exc))






# ── Enums ──

class ExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeType(StrEnum):
    START = "start"
    END = "end"
    AGENT = "agent"
    TOOL = "tool"
    CONDITION = "condition"
    ITERATOR = "iterator"
    CODE = "code"
    TRANSFORM = "transform"


# ── Data Contracts ──

@dataclass
class ExecutionContext:
    session_id: str
    user_id: str
    variables: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    status: ExecutionStatus
    output: Any = None
    error: str | None = None
    logs: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCall:
    tool_name: str
    arguments: dict[str, Any]
    call_id: str = ""


@dataclass
class ToolResult:
    call_id: str
    output: str
    error: str | None = None


# ── Interfaces ──

class IModelAdapter(ABC):
    provider: str
    model_id: str
    capabilities: Any

    @abstractmethod
    async def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def stream(self, messages: list[dict[str, Any]], **kwargs: Any) -> AsyncIterator[str]:
        raise NotImplementedError


class IToolRegistry(ABC):
    @abstractmethod
    def register(self, name: str, description: str, parameters: dict[str, Any], func: Callable[..., Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def execute(self, name: str, arguments: dict[str, Any]) -> str:
        raise NotImplementedError

    @abstractmethod
    def list_tools(self) -> list[dict[str, Any]]:
        raise NotImplementedError


class ISkillRegistry(ABC):
    @abstractmethod
    def register(self, skill: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, skill_id: str) -> Any | None:
        raise NotImplementedError

    @abstractmethod
    def list_skills(self) -> list[dict[str, Any]]:
        raise NotImplementedError


class IExecutor(ABC):
    @abstractmethod
    async def execute(self, context: ExecutionContext, **kwargs: Any) -> ExecutionResult:
        raise NotImplementedError

    @abstractmethod
    def execute_stream(self, context: ExecutionContext, **kwargs: Any) -> AsyncIterator[Any]:
        raise NotImplementedError

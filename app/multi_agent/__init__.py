"""Multi-agent collaboration system (CrewAI style)."""

from __future__ import annotations

import asyncio
import uuid
from enum import Enum, StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AgentRole(BaseModel):
    """Definition of an agent's role and capabilities."""

    name: str
    role: str
    goal: str
    backstory: str
    tools: list[str] = Field(default_factory=list)
    can_delegate: bool = True


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentTask(BaseModel):
    """A task assigned to an agent."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    expected_output: str
    agent_name: str
    context: str = ""
    status: TaskStatus = TaskStatus.PENDING
    result: str = ""
    error: str = ""


class CrewOutput(BaseModel):
    """Output from a crew execution."""

    crew_id: str
    results: list[dict[str, Any]]
    final_output: str
    total_iterations: int

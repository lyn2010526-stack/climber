"""Group API schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.api_v1.base import StrictRequest


class GroupCreateRequest(StrictRequest):
    name: str = "New Group"
    description: str = ""
    topic: str = ""
    status: str = "active"
    max_rounds: int = Field(default=10, ge=1)
    process_type: str = "sequential"
    template: Literal["default"] | None = None


class GroupMemberCreateRequest(StrictRequest):
    agent_id: str
    role: str = "participant"
    model_provider: str | None = None
    model_id: str | None = None
    api_key: str | None = None
    api_key_encrypted: str | None = None
    tools: list[str] = Field(default_factory=list)
    is_worker: bool = False


class GroupMemberUpdateRequest(StrictRequest):
    role: str | None = None
    status: str | None = None
    is_worker: bool | None = None
    current_task_id: str | None = None

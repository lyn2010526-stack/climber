"""Group API schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from app.schemas.api_v1.base import PublicResponse, StrictRequest


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


class GroupMemberResponse(PublicResponse):
    id: str
    agent_id: str
    role: str
    status: str
    is_worker: bool
    model_provider: str | None = None
    model_id: str | None = None
    tools: list[str] = Field(default_factory=list)
    message_count: int = 0
    last_active: str | None = None
    current_task_id: str | None = None


class GroupResponse(PublicResponse):
    id: str
    name: str
    description: str = ""
    topic: str = ""
    status: str
    max_rounds: int
    process_type: str
    manager_agent_id: str | None = None
    manager_llm: str | None = None
    member_count: int = 0
    members: list[GroupMemberResponse] = Field(default_factory=list)
    created_at: str = ""


class GroupMessagesResponse(PublicResponse):
    messages: list[dict[str, Any]] = Field(default_factory=list)

"""Agent API schemas."""

from __future__ import annotations

from pydantic import Field

from app.schemas.api_v1.base import PublicResponse, StrictRequest


class AgentCreateRequest(StrictRequest):
    name: str = Field(min_length=1)
    description: str = ""
    provider: str = "openai"
    model_id: str = "gpt-4o-mini"
    base_url: str | None = None
    api_key: str | None = None
    api_key_encrypted: str | None = None
    system_prompt: str = ""
    tool_ids: list[str] = Field(default_factory=list)
    skill_ids: list[str] = Field(default_factory=list)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)


class AgentResponse(PublicResponse):
    id: str
    name: str
    description: str = ""
    provider: str
    model_id: str
    system_prompt: str = ""
    base_url: str | None = None
    tool_ids: list[str] = Field(default_factory=list)
    skill_ids: list[str] = Field(default_factory=list)
    temperature: float = 0.7
    max_tokens: int | None = None
    created_at: str | None = None

"""Skill API schemas."""

from __future__ import annotations

from pydantic import Field

from app.schemas.api_v1.base import PublicResponse, StrictRequest


class SkillResponse(PublicResponse):
    id: str
    name: str
    description: str = ""
    category: str
    prompt_template: str = ""
    tools: list[str] = Field(default_factory=list)
    is_enabled: bool
    use_count: int = 0
    path: str = ""


class SkillToggleResponse(PublicResponse):
    ok: bool
    id: str
    is_enabled: bool


class SkillDeleteResponse(PublicResponse):
    ok: bool
    deleted: str

class SkillCreateRequest(StrictRequest):
    name: str = Field(min_length=1)
    description: str = ""
    category: str = "general"
    prompt_template: str = ""
    tools: list[str] = Field(default_factory=list)

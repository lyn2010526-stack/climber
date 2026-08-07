"""Skill API schemas."""

from __future__ import annotations

from pydantic import Field

from app.schemas.api_v1.base import StrictRequest


class SkillCreateRequest(StrictRequest):
    name: str = Field(min_length=1)
    description: str = ""
    category: str = "general"
    prompt_template: str = ""
    tools: list[str] = Field(default_factory=list)

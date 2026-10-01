"""Skill API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.api_v1.base import StrictRequest


class SkillCreateRequest(StrictRequest):
    name: str = Field(min_length=1)
    description: str = ""
    category: str = "general"
    prompt_template: str = ""
    tools: list[str] = Field(default_factory=list)


class SkillVersionCreateRequest(StrictRequest):
    """Body for storing a skill's content as a new version.

    Omitted fields fall back to the skill's current prompt and tools.
    """

    prompt: str | None = None
    tools: list[str] | None = None
    version: str | None = Field(default=None, max_length=20)
    author: str | None = None
    changelog: str = ""


class SkillTestCaseCreateRequest(StrictRequest):
    """Body for adding a test case to a skill."""

    name: str = Field(min_length=1)
    input_params: dict[str, Any] = Field(default_factory=dict)
    expected_output_contains: str = ""
    expected_tools: list[str] = Field(default_factory=list)
    timeout_seconds: int = Field(default=30, ge=1)

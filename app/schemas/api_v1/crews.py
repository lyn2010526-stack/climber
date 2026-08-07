"""Crew API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.api_v1.base import StrictRequest


class CrewCreateRequest(StrictRequest):
    name: str = Field(min_length=1)
    description: str = ""
    process: str = "sequential"
    agents: list[dict[str, Any]] = Field(default_factory=list)
    tasks: list[dict[str, Any]] = Field(default_factory=list)


class CrewRunRequest(StrictRequest):
    agent_id: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)

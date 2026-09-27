"""Crew API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.api_v1.base import PublicResponse, StrictRequest


class CrewCreateRequest(StrictRequest):
    name: str = Field(min_length=1)
    description: str = ""
    process: str = "sequential"
    agents: list[dict[str, Any]] = Field(default_factory=list)
    tasks: list[dict[str, Any]] = Field(default_factory=list)


class CrewRunRequest(StrictRequest):
    agent_id: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)


class CrewResponse(PublicResponse):
    id: str
    name: str
    description: str = ""
    process: str
    agents: list[dict[str, Any]] = Field(default_factory=list)
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    run_count: int = 0
    created_at: str | None = None


class CrewRunResponse(PublicResponse):
    id: str
    run_id: str
    status: str
    output: str = ""
    task_results: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None

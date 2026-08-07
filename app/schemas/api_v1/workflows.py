"""Workflow API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.api_v1.base import StrictRequest


class WorkflowCreateRequest(StrictRequest):
    name: str = "Untitled Workflow"
    description: str = ""
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)


class WorkflowUpdateRequest(StrictRequest):
    name: str | None = None
    description: str | None = None
    nodes: list[dict[str, Any]] | None = None
    edges: list[dict[str, Any]] | None = None


class WorkflowRunRequest(StrictRequest):
    agent_id: str | None = None
    nodes: list[dict[str, Any]] | None = None
    edges: list[dict[str, Any]] | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    workflow_id: str = ""

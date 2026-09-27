"""Workflow API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.api_v1.base import PublicResponse, StrictRequest


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


class WorkflowResponse(PublicResponse):
    """Public workflow representation."""

    id: str
    name: str
    description: str = ""
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    is_template: bool = False
    run_count: int = 0
    last_status: str | None = None
    created_at: str | None = None


class WorkflowRunResponse(PublicResponse):
    """Workflow execution result."""

    id: str
    status: str
    outputs: dict[str, Any] = Field(default_factory=dict)
    node_results: dict[str, Any] = Field(default_factory=dict)
    execution_time_ms: float | None = None
    error: str | None = None

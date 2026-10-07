"""Task API schemas — mirroring the actual /tasks endpoints.

The task worker is invoked through ``task_manager.submit(task_type, payload)``,
so the submit request carries the handler type plus an opaque payload. Keeping
this schema in sync with ``app.api/v1/routes/tasks.py`` avoids drift between
the documented contract and the endpoint body.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from app.schemas.api_v1.base import PublicResponse, StrictRequest

TaskType = Literal["agent_run", "factory_run", "data_processing", "workflow"]
SubtaskStatus = Literal[
    "pending",
    "ready",
    "claimed",
    "running",
    "retrying",
    "completed",
    "failed",
    "blocked",
    "skipped",
    "dead_letter",
]


class SubmitTaskRequest(StrictRequest):
    task_type: TaskType
    payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_factory_payload(self) -> SubmitTaskRequest:
        if self.task_type == "factory_run" and not str(self.payload.get("objective", "")).strip():
            raise ValueError("factory_run payload requires a non-empty objective")
        return self


class ClaimSubtasksRequest(StrictRequest):
    agent_id: str = Field(min_length=1)
    worker_id: str | None = Field(default=None, min_length=1)
    limit: int = Field(default=1, ge=1, le=50)
    lease_seconds: int = Field(default=900, ge=1, le=86400)


class CompleteSubtaskRequest(StrictRequest):
    agent_id: str = Field(min_length=1)
    claim_token: str | None = Field(default=None, min_length=1)
    lease_version: int | None = Field(default=None, ge=1)
    completion_id: str | None = Field(default=None, min_length=1)
    result: Any = None
    error: str | None = None


class HeartbeatSubtaskRequest(StrictRequest):
    agent_id: str = Field(min_length=1)
    claim_token: str = Field(min_length=1)
    lease_version: int = Field(ge=1)
    extend_seconds: int = Field(default=300, ge=1, le=86400)


class SubtaskResponse(PublicResponse):
    subtask_id: str = Field(validation_alias="id", serialization_alias="subtask_id")
    description: str
    status: SubtaskStatus
    dependencies: list[str] = Field(default_factory=list)
    result: Any = None
    error: str = ""
    claimed_by: str | None = None
    claimed_at: str | None = None
    lease_expires_at: float | None = None
    claim_token: str | None = None
    lease_version: int = 0
    attempt: int = 0
    worker_id: str | None = None
    heartbeat_at: str | None = None
    completion_id: str | None = None
    completed_at: str | None = None


class SubtaskListResponse(PublicResponse):
    task_id: str
    subtasks: list[SubtaskResponse]


class TaskResponse(PublicResponse):
    task_id: str
    objective: str = ""
    status: str
    progress: int = 0
    total_steps: int = 0
    result: Any = None
    error: str | None = None
    retry_count: int = 0
    checkpoint: dict[str, Any] | None = None
    progress_evaluation: dict[str, Any] | None = None
    interruption_reason: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None

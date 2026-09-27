"""Scheduler API response schemas."""

from __future__ import annotations

from app.schemas.api_v1.base import DeleteResponse, PublicResponse


class ScheduledWorkflowResponse(PublicResponse):
    id: str
    name: str
    schedule: str | None = None
    last_status: str | None = None
    run_count: int = 0


class SchedulerTaskResponse(PublicResponse):
    id: str
    name: str
    cron: str | None = None
    description: str = ""
    enabled: bool = True
    last_run: str | None = None
    next_run: str | None = None
    run_count: int = 0


SchedulerDeleteResponse = DeleteResponse

"""Task API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.api_v1.base import StrictRequest


class TaskCreateRequest(StrictRequest):
    group_id: str
    description: str = Field(min_length=1)
    worker_id: str | None = None
    reviewer_ids: list[str] = Field(default_factory=list)
    max_rounds: int = Field(default=5, ge=1)
    context: list[str] = Field(default_factory=list)
    guardrails: list[dict[str, Any]] = Field(default_factory=list)
    human_review_required: bool = False
    output_schema: dict[str, Any] = Field(default_factory=dict)

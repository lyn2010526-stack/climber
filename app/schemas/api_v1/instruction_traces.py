"""User instruction trace API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.api_v1.base import PublicResponse, StrictRequest
from app.storage.models_instruction_traces import InstructionSource


class InstructionTraceCreate(StrictRequest):
    """Archive one user instruction verbatim."""

    raw_text: str = Field(min_length=1)
    session_id: str | None = None
    user_id: str | None = None
    source: InstructionSource = InstructionSource.CHAT
    intent_summary: str | None = None
    task_spec: dict[str, Any] | None = None
    token_count: int | None = Field(default=None, ge=0)
    dedup_window_seconds: int | None = Field(default=None, ge=0)
    client_sent_at: str | None = None


class InstructionTraceRead(PublicResponse):
    id: str
    session_id: str | None
    user_id: str | None
    raw_text: str
    intent_summary: str | None
    task_spec: dict[str, Any] | None
    goal_preserved: bool
    source: InstructionSource
    token_count: int
    compressed_into_id: str | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class InstructionTracePage(PublicResponse):
    items: list[InstructionTraceRead]
    total: int
    limit: int
    offset: int
    deduplicated: int = 0

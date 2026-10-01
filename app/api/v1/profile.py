"""User profile endpoints.

Exposes the persisted profile loop: events are appended through the privacy
boundary of ``ProfileLoopService``, summaries are rebuilt from the durable
event log and cached as per-user snapshots, and suggestions stay auxiliary to
the current instruction by construction.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field

from app.core.auth import get_current_user
from app.core.profile.persistence import ProfileStore
from app.schemas.api_v1.base import PublicResponse, StrictRequest

if TYPE_CHECKING:
    from app.storage.models_user_profile import UserProfileEvent

router = APIRouter()

store = ProfileStore()


class ProfileEventCreate(StrictRequest):
    """Record one Agent-internal interaction signal."""

    instruction: str = Field(min_length=1)
    task_type: str = Field(min_length=1)
    outcome: Literal["success", "failure"]
    interrupted: bool = False
    retried: bool = False
    reasoning_level: str = "standard"
    tool: str | None = None
    feedback: Literal["positive", "negative", "neutral"] = "neutral"
    occurred_at: datetime | None = None
    source: str = "agent_internal"


class ProfileEventRead(PublicResponse):
    id: str
    user_id: str
    task_type: str
    tool: str | None
    reasoning_level: str
    outcome: str
    feedback: str | None
    interrupted: bool
    retried: bool
    source: str
    occurred_at: datetime
    created_at: datetime


class ProfileSummaryRead(PublicResponse):
    task_preferences: dict[str, float]
    tool_preferences: dict[str, float]
    reasoning_preferences: dict[str, float]
    retry_rate: float
    interruption_rate: float
    success_rate: float
    confidence: float
    provenance: list[str]
    enabled: bool
    persona_cluster: int | None = None
    persona_cluster_confidence: float = 0.0


def _to_read(row: UserProfileEvent) -> ProfileEventRead:
    return ProfileEventRead(
        id=row.id,
        user_id=row.user_id,
        task_type=row.task_type,
        tool=row.tool,
        reasoning_level=row.reasoning_level,
        outcome=row.outcome,
        feedback=row.feedback,
        interrupted=bool(row.interrupted),
        retried=bool(row.retried),
        source=row.source,
        occurred_at=row.occurred_at,
        created_at=row.created_at,
    )


@router.post("/events", response_model=ProfileEventRead)
async def record_profile_event(
    payload: ProfileEventCreate,
    user_id: str = Depends(get_current_user),
) -> ProfileEventRead:
    """Persist one profile event after the privacy-boundary check."""
    fields = payload.model_dump()
    if fields["occurred_at"] is None:
        fields["occurred_at"] = datetime.now(UTC)
    try:
        row = await store.record_event(user_id, **fields)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if row.id is None:
        raise HTTPException(status_code=500, detail="Profile event was not stored")
    return _to_read(row)


@router.get("/summary", response_model=ProfileSummaryRead)
async def get_profile_summary(
    user_id: str = Depends(get_current_user),
) -> ProfileSummaryRead:
    """Rebuild the user's profile summary from the stored event log."""
    return await store.summary(user_id)


@router.get("/suggestions")
async def get_profile_suggestions(
    current_instruction: str | None = Query(default=None),
    user_id: str = Depends(get_current_user),
) -> dict[str, object]:
    """Return profile hints that never override the current instruction."""
    return await store.suggestions(user_id, current_instruction or "")

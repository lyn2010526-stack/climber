"""Data access for the user profile event log and snapshot cache.

Events are append-only and replayed oldest-first, which matches the
time-decay and streaming-cluster semantics of the in-memory profile loop.
Snapshots are keyed by user so recomputation folds into a single row instead
of accumulating summary history.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import select

from app.storage.models_user_profile import UserProfileEvent, UserProfileSnapshot

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_LIST_LIMIT = 500
DEFAULT_SOURCE = "agent_internal"


async def append_event(
    db: AsyncSession,
    *,
    user_id: str,
    task_type: str,
    outcome: str,
    tool: str | None = None,
    reasoning_level: str = "standard",
    feedback: str | None = "neutral",
    interrupted: bool = False,
    retried: bool = False,
    source: str = DEFAULT_SOURCE,
    occurred_at: datetime | None = None,
) -> UserProfileEvent:
    """Append one profile event and return the stored row."""
    event = UserProfileEvent(
        id=str(uuid4()),
        user_id=user_id,
        task_type=task_type,
        outcome=outcome,
        tool=tool,
        reasoning_level=reasoning_level,
        feedback=feedback,
        interrupted=interrupted,
        retried=retried,
        source=source,
        occurred_at=occurred_at or datetime.now(UTC),
    )
    db.add(event)
    await db.flush()
    return event


async def list_events(
    db: AsyncSession,
    user_id: str,
    *,
    limit: int = DEFAULT_LIST_LIMIT,
    occurred_after: datetime | None = None,
) -> Sequence[UserProfileEvent]:
    """Return one user's profile events oldest-first, optionally after a mark."""
    stmt = select(UserProfileEvent).where(UserProfileEvent.user_id == user_id)
    if occurred_after is not None:
        stmt = stmt.where(UserProfileEvent.occurred_at > occurred_after)
    result = await db.execute(
        stmt.order_by(UserProfileEvent.occurred_at.asc(), UserProfileEvent.id.asc()).limit(limit)
    )
    return result.scalars().all()


async def get_snapshot(db: AsyncSession, user_id: str) -> UserProfileSnapshot | None:
    """Return the persisted summary snapshot for one user, if any."""
    result = await db.execute(
        select(UserProfileSnapshot).where(UserProfileSnapshot.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def upsert_snapshot(
    db: AsyncSession,
    *,
    user_id: str,
    payload: dict,
    confidence: float,
) -> UserProfileSnapshot:
    """Write the latest summary projection, folding into the existing row."""
    snapshot = await get_snapshot(db, user_id)
    if snapshot is None:
        snapshot = UserProfileSnapshot(
            user_id=user_id,
            payload=payload,
            confidence=confidence,
        )
        db.add(snapshot)
    else:
        snapshot.payload = payload
        snapshot.confidence = confidence
    await db.flush()
    return snapshot

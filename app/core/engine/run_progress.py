"""Durable snapshot of in-flight agent run progress for crash recovery.

The Pi outer loop emits LOOP_STATUS events carrying the current subtask,
completed subtasks and queue mirrors. ``record_loop_progress`` mirrors those
onto a persistent row so a crash or restart can either resume the run or mark
it interrupted. All writes are fail-open: an observability/storage outage never
changes the loop behaviour or raises into the caller.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

logger = logging.getLogger(__name__)

TERMINAL_STATUSES = {"completed", "failed", "cancelled", "stopped"}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _default_factory():
    from app.storage import async_session

    return async_session


class RunProgressStore:
    """Upsert-only snapshot store keyed by session id."""

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or _default_factory()

    async def record_progress(
        self,
        session_id: str,
        user_id: str | None = None,
        turn_id: str | None = None,
        *,
        outer_round: int = 0,
        current_subtask: str | None = None,
        completed_subtasks: list[str] | None = None,
        followup_queue: list[str] | None = None,
        steering_queue: list[str] | None = None,
    ) -> bool:
        """Upsert the latest in-progress snapshot for a session."""
        from app.storage.database import RunProgressRecord

        values = {
            "user_id": str(user_id or ""),
            "turn_id": str(turn_id or ""),
            "status": "in_progress",
            "outer_round": int(outer_round or 0),
            "current_subtask": str(current_subtask or "")[:2000],
            "completed_subtasks_json": json.dumps(list(completed_subtasks or []), ensure_ascii=False),
            "followup_queue_json": json.dumps(list(followup_queue or []), ensure_ascii=False),
            "steering_queue_json": json.dumps(list(steering_queue or []), ensure_ascii=False),
            "heartbeat_at": _now(),
        }
        try:
            async with self.session_factory() as db:
                existing = await db.get(RunProgressRecord, str(session_id))
                if existing is None:
                    db.add(RunProgressRecord(session_id=str(session_id), **values))
                else:
                    for key, value in values.items():
                        setattr(existing, key, value)
                await db.commit()
            return True
        except Exception as exc:
            logger.warning("run_progress.record_failed", exc_info=exc)
            return False

    async def mark_completed(self, session_id: str) -> bool:
        return await self._finalize(session_id, "completed", reason="")

    async def mark_interrupted(self, session_id: str, reason: str = "") -> bool:
        return await self._finalize(session_id, "interrupted", reason=reason or "interrupted")

    async def _finalize(self, session_id: str, status: str, reason: str = "") -> bool:
        from app.storage.database import RunProgressRecord

        try:
            async with self.session_factory() as db:
                existing = await db.get(RunProgressRecord, str(session_id))
                if existing is None:
                    return False
                existing.status = status
                if reason:
                    existing.current_subtask = str(reason)[:2000]
                existing.heartbeat_at = _now()
                await db.commit()
            return True
        except Exception as exc:
            logger.warning("run_progress.finalize_failed", exc_info=exc)
            return False

    async def get_progress(self, session_id: str) -> dict[str, object] | None:
        from app.storage.database import RunProgressRecord

        try:
            async with self.session_factory() as db:
                row = await db.get(RunProgressRecord, str(session_id))
                if row is None:
                    return None
                return {
                    "session_id": row.session_id,
                    "user_id": row.user_id,
                    "turn_id": row.turn_id,
                    "status": row.status,
                    "outer_round": row.outer_round,
                    "current_subtask": row.current_subtask,
                    "completed_subtasks": json.loads(row.completed_subtasks_json or "[]"),
                    "followup_queue": json.loads(row.followup_queue_json or "[]"),
                    "steering_queue": json.loads(row.steering_queue_json or "[]"),
                    "heartbeat_at": row.heartbeat_at,
                }
        except Exception as exc:
            logger.warning("run_progress.get_failed", exc_info=exc)
            return None

    async def list_in_progress(self, user_id: str | None = None) -> list[str]:
        from app.storage.database import RunProgressRecord

        try:
            async with self.session_factory() as db:
                query = select(RunProgressRecord).where(RunProgressRecord.status == "in_progress")
                if user_id:
                    query = query.where(RunProgressRecord.user_id == str(user_id))
                rows = (await db.execute(query)).scalars().all()
                return [row.session_id for row in rows]
        except Exception as exc:
            logger.warning("run_progress.list_failed", exc_info=exc)
            return []

    async def mark_stale_interrupted(self, max_age_minutes: float = 30) -> int:
        """Startup recovery: flip in_progress snapshots with a stale heartbeat."""
        from app.storage.database import RunProgressRecord

        cutoff = _now() - timedelta(minutes=max_age_minutes)
        marked = 0
        try:
            async with self.session_factory() as db:
                rows = (
                    await db.execute(
                        select(RunProgressRecord).where(
                            RunProgressRecord.status == "in_progress",
                            RunProgressRecord.heartbeat_at < cutoff,
                        )
                    )
                ).scalars().all()
                for row in rows:
                    row.status = "interrupted"
                    row.heartbeat_at = _now()
                    marked += 1
                await db.commit()
            return marked
        except Exception as exc:
            logger.warning("run_progress.stale_mark_failed", exc_info=exc)
            return 0


def build_loop_snapshot(session: object, loop_payload: dict[str, object]) -> dict[str, object]:
    """Project a LOOP_STATUS payload onto the snapshot row fields."""
    return {
        "session_id": str(getattr(session, "session_id", "")),
        "user_id": getattr(session, "user_id", None),
        "turn_id": getattr(session, "current_turn_id", None),
        "outer_round": int(loop_payload.get("outer_round", 0) or 0),
        "current_subtask": loop_payload.get("current_input"),
        "completed_subtasks": loop_payload.get("completed", []),
        "followup_queue": loop_payload.get("followup_queue", []),
        "steering_queue": loop_payload.get("steering_queue", []),
    }


def _engine_factory(engine: object):
    return getattr(getattr(engine, "_run_store", None), "session_factory", None) or _default_factory()


async def record_loop_progress(engine: object, session: object, loop_payload: dict[str, object]) -> bool:
    """Mirror a LOOP_STATUS payload onto the durable snapshot (fail-open)."""
    try:
        store = RunProgressStore(_engine_factory(engine))
        return await store.record_progress(**build_loop_snapshot(session, loop_payload))
    except Exception:
        return False


async def finalize_run_progress(engine: object, session: object) -> bool:
    """Close the durable snapshot once the run reaches a terminal outcome.

    A completed run is recorded as such; every other terminal outcome is marked
    interrupted so startup recovery can surface untracked sessions.
    """
    try:
        status = getattr(session, "_run_status_override", None) or getattr(session, "status").value
        store = RunProgressStore(_engine_factory(engine))
        if status == "completed":
            return await store.mark_completed(str(session.session_id))
        reason = getattr(session, "_last_error", None) or status or "interrupted"
        return await store.mark_interrupted(str(session.session_id), reason=str(reason))
    except Exception:
        return False
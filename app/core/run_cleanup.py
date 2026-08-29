"""Background maintenance for persisted Runs and raw payloads.

`cleanup_stale_runs` marks long-lived active Runs as failed so a crashed or
orphaned executor cannot pin a session forever. `cleanup_expired_raw_payloads`
reclaims `debug`-policy payloads after their retention window. Both sweepers
are designed to be idempotent and failure-isolated: one bad Run never aborts
the whole pass.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.core.run_protocol import (
    TERMINATION_REASON_INTERRUPTED,
    RunPage,
    RunRecord,
    RunStateConflictError,
    RunStatus,
    termination_metadata,
)

logger = structlog.get_logger(__name__)

_ACTIVE_STATUSES = (
    RunStatus.PENDING,
    RunStatus.RUNNING,
    RunStatus.PAUSED,
)

_DEFAULT_PAGE_LIMIT = 50


def _run_start_ref(run: RunRecord) -> datetime:
    """Earliest credible point the Run began occupying an executor slot."""
    return run.started_at if run.started_at is not None else run.created_at or datetime.now(UTC)


def _stale_error(*, age: timedelta) -> dict[str, Any]:
    return {
        "code": "stale_run",
        "message": f"Run exceeded its maximum age of {age} without progressing and was marked failed",
    }


async def cleanup_stale_runs(
    store: Any,
    *,
    max_age: timedelta,
    now: datetime | None = None,
    page_limit: int = _DEFAULT_PAGE_LIMIT,
) -> int:
    """Mark active Runs older than ``max_age`` as failed.

    A Run counts as stalled when its ``started_at`` (or ``created_at`` when
    never started) predates ``now - max_age``. Transitioning is best-effort:
    each Run is guarded independently and ``RunStateConflictError`` is logged
    rather than propagated. Returns the number of Runs transitioned.
    """
    reference = now or datetime.now(UTC)
    threshold = reference - max_age
    swept = 0
    for status in _ACTIVE_STATUSES:
        offset = 0
        while True:
            page: RunPage = await store.list_runs(
                status=status,
                limit=page_limit,
                offset=offset,
            )
            for run in page.items:
                if _run_start_ref(run) >= threshold:
                    continue
                try:
                    stale_error = _stale_error(age=max_age)
                    await store.transition(
                        run.run_id,
                        status,
                        RunStatus.FAILED,
                        values={
                            "error": stale_error,
                            "error_message": stale_error["message"],
                            "metadata": termination_metadata(
                                TERMINATION_REASON_INTERRUPTED,
                                detail="stale_run",
                            ),
                        },
                    )
                    swept += 1
                    logger.warning(
                        "run_cleanup.stale_run_marked_failed",
                        run_id=run.run_id,
                        status=status.value,
                        age=str(reference - _run_start_ref(run)),
                    )
                except RunStateConflictError as exc:
                    logger.info(
                        "run_cleanup.stale_run_conflict",
                        run_id=run.run_id,
                        error=str(exc),
                    )
            if len(page.items) < page_limit:
                break
            offset += page_limit
    return swept


async def cleanup_expired_raw_payloads(
    store: Any,
    *,
    now: datetime | None = None,
) -> int:
    """Reclaim raw payload records past their retention window."""
    awaitable = store.cleanup_expired_raw_payloads
    if not callable(awaitable):
        raise TypeError("RunStore does not implement cleanup_expired_raw_payloads")
    return await awaitable(now=now)

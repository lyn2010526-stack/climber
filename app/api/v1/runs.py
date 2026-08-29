"""Run management endpoints over the unified Run protocol.

Exposes the RunRuntime seam (detail, list, cancel, resume) that the legacy
Agent Chat slice built but never surfaced over HTTP.  The endpoints delegate
to the AgentEngineRunAdapter and its durable store so state transitions are
fenced and events stay replayable.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.api.v1.chat import get_engine, get_run_adapter
from app.core.auth import get_current_user
from app.core.run_protocol import (
    ResumeRun,
    RunNotFoundError,
    RunStatus,
)
from app.storage import async_session
from app.storage.database import Message as MessageModel

router = APIRouter(prefix="/runs", dependencies=[Depends(get_current_user)])


def _run_payload(run: Any) -> dict[str, Any]:
    return run.to_dict()


@router.get("/{run_id}")
async def get_run(run_id: str, user_id: str = Depends(get_current_user)) -> dict[str, Any]:
    """Return one Run's lifecycle state plus its persisted messages."""
    adapter = get_run_adapter(get_engine())
    try:
        run = await adapter.require_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if run.user_id and run.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    payload = _run_payload(run)
    payload["messages"] = await _messages_for_run(run_id)
    return payload


async def _messages_for_run(run_id: str) -> list[dict[str, Any]]:
    async with async_session() as db:
        rows = (
            await db.execute(
                select(MessageModel)
                .where(MessageModel.run_id == run_id)
                .order_by(MessageModel.created_at.asc())
            )
        ).scalars().all()
    return [
        {
            "id": row.id,
            "role": row.role,
            "content": row.content,
            "tool_name": row.tool_name,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@router.get("")
async def list_runs(
    session_id: str | None = Query(default=None, max_length=128),
    status: RunStatus | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user_id: str = Depends(get_current_user),
) -> dict[str, Any]:
    """List Runs with offset pagination, newest first."""
    adapter = get_run_adapter(get_engine())
    page = await adapter.list_runs(
        session_id=session_id,
        user_id=user_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [_run_payload(run) for run in page.items],
        "total": page.total,
        "limit": page.limit,
        "offset": page.offset,
        "has_more": page.offset + len(page.items) < page.total,
    }


@router.get("/{run_id}/events")
async def get_run_events(
    run_id: str,
    after: int = Query(default=0, ge=0),
    limit: int = Query(default=256, ge=1, le=1024),
    user_id: str = Depends(get_current_user),
) -> dict[str, Any]:
    """Replay a Run's persisted event stream."""
    adapter = get_run_adapter(get_engine())
    try:
        run = await adapter.require_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if run.user_id and run.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    page = await adapter.replay(run.run_id, after=after, limit=limit)
    return {
        "run_id": run.run_id,
        "after": after,
        "oldest_sequence": page.oldest_sequence,
        "latest_sequence": page.latest_sequence,
        "has_gap": page.has_gap,
        "has_more": page.has_more,
        "next_after": page.next_after,
        "unknown_event_types": list(page.unknown_event_types),
        "events": [
            {
                "sequence": event.sequence,
                "event_id": event.event_id,
                "event": event.event_type,
                "data": event.data,
                "trace_id": event.trace_id,
                "checkpoint_id": event.checkpoint_id,
            }
            for event in page.events
        ],
    }


@router.post("/{run_id}/cancel")
async def cancel_run(run_id: str, user_id: str = Depends(get_current_user)) -> dict[str, Any]:
    """Cancel an in-flight Run and persist a terminal event."""
    adapter = get_run_adapter(get_engine())
    try:
        run = await adapter.require_run(run_id)
        if run.user_id and run.user_id != user_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        state = await adapter.cancel(run_id, actor_id=user_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _run_payload(state)


@router.post("/{run_id}/resume")
async def resume_run(run_id: str, user_id: str = Depends(get_current_user)) -> dict[str, Any]:
    """Resume a persisted Run so its stream can continue."""
    adapter = get_run_adapter(get_engine())
    try:
        run = await adapter.require_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if run.user_id and run.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    handle = await adapter.resume(
        ResumeRun(
            run_id=run.run_id,
            session_id=run.session_id,
            user_id=user_id,
            execution_token=run.execution_token,
            checkpoint_id=run.checkpoint_id,
        )
    )
    return {"run_id": handle.run_id, "session_id": handle.session_id, "status": handle.status.value}

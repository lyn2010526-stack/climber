"""User instruction trace endpoints.

Archives every instruction the user issues so the intent survives context-window
eviction and model swaps. Writes are deduplicated on the server, so a client may
retry a submission without creating a second archive row.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import get_current_user
from app.schemas.api_v1.instruction_traces import (
    InstructionTraceCreate,
    InstructionTracePage,
    InstructionTraceRead,
)
from app.storage import async_session
from app.storage.models_instruction_traces import InstructionTrace
from app.storage.repository_instruction_traces import (
    DEFAULT_DEDUP_WINDOW_SECONDS,
    count_traces,
    create_trace,
    list_traces,
)

router = APIRouter()

MAX_PAGE_SIZE = 200


def _to_read(trace: InstructionTrace) -> InstructionTraceRead:
    return InstructionTraceRead(
        id=trace.id,
        session_id=trace.session_id,
        user_id=trace.user_id,
        raw_text=trace.raw_text,
        intent_summary=trace.intent_summary,
        task_spec=trace.task_spec,
        goal_preserved=bool(trace.goal_preserved),
        source=trace.source,
        token_count=trace.token_count,
        compressed_into_id=trace.compressed_into_id,
        is_archived=bool(trace.is_archived),
        created_at=trace.created_at,
        updated_at=trace.updated_at,
    )


@router.post("", response_model=InstructionTraceRead)
@router.post("/", response_model=InstructionTraceRead)
async def create_instruction_trace(
    payload: InstructionTraceCreate,
    user_id: str = Depends(get_current_user),
) -> InstructionTraceRead:
    """Archive one instruction verbatim, reusing a recent identical row."""
    effective_user = payload.user_id or user_id
    window = (
        payload.dedup_window_seconds
        if payload.dedup_window_seconds is not None
        else DEFAULT_DEDUP_WINDOW_SECONDS
    )
    async with async_session() as db:
        trace, _ = await create_trace(
            db,
            {
                "raw_text": payload.raw_text,
                "session_id": payload.session_id,
                "user_id": effective_user,
                "source": payload.source,
                "intent_summary": payload.intent_summary,
                "task_spec": payload.task_spec,
            },
            dedup_window_seconds=window,
            token_count=payload.token_count,
        )
        await db.commit()
        if trace.id is None:
            raise HTTPException(status_code=500, detail="Instruction trace was not stored")
        return _to_read(trace)


@router.get("", response_model=InstructionTracePage)
@router.get("/", response_model=InstructionTracePage)
async def list_instruction_traces(
    session_id: str | None = None,
    user_id: str | None = None,
    is_archived: bool | None = None,
    limit: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
) -> InstructionTracePage:
    """List archived instructions with optional filters and pagination."""
    async with async_session() as db:
        rows = await list_traces(
            db,
            session_id=session_id,
            user_id=user_id,
            is_archived=is_archived,
            limit=limit,
            offset=offset,
        )
        total = await count_traces(
            db,
            session_id=session_id,
            user_id=user_id,
            is_archived=is_archived,
        )
        return InstructionTracePage(
            items=[_to_read(row) for row in rows],
            total=total,
            limit=limit,
            offset=offset,
        )

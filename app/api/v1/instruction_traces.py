"""User instruction trace endpoints.

Archives every instruction the user issues so the intent survives context-window
eviction and model swaps. Writes are deduplicated on the server, so a client may
retry a submission without creating a second archive row.
"""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.core.instruction.understanding import understand_instruction
from app.schemas.api_v1.instruction_traces import (
    InstructionTraceCreate,
    InstructionTracePage,
    InstructionTraceRead,
)
from app.storage import async_session
from app.storage.models_instruction_traces import InstructionSource, InstructionTrace
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
        source=cast(InstructionSource, trace.source),
        token_count=trace.token_count,
        compressed_into_id=trace.compressed_into_id,
        is_archived=bool(trace.is_archived),
        turn_id=trace.turn_id,
        status=trace.status,
        outcome=trace.outcome,
        retrieval_count=trace.retrieval_count,
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
    requested_user_id: str | None = Query(default=None, alias="user_id"),
    is_archived: bool | None = None,
    limit: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    current_user: str = Depends(get_current_user),
) -> InstructionTracePage:
    """List archived instructions with optional filters and pagination."""
    if requested_user_id is not None and requested_user_id != current_user:
        raise HTTPException(status_code=403, detail="Forbidden")
    async with async_session() as db:
        rows = await list_traces(
            db,
            session_id=session_id,
            user_id=current_user,
            is_archived=is_archived,
            limit=limit,
            offset=offset,
        )
        total = await count_traces(
            db,
            session_id=session_id,
            user_id=current_user,
            is_archived=is_archived,
        )
        return InstructionTracePage(
            items=[_to_read(row) for row in rows],
            total=total,
            limit=limit,
            offset=offset,
        )


class InstructionUnderstandRequest(BaseModel):
    """Payload for the read-only instruction understanding endpoint."""

    raw_text: str = ""
    context: str | None = None


@router.post("/understand")
async def understand_instruction_endpoint(
    payload: InstructionUnderstandRequest,
) -> dict[str, object]:
    """Return the structured, deterministic understanding of a user instruction.

    Mirrors the trace ``task_spec`` shape: main goal, constraints, ambiguities,
    confidence, clarification questions and a plain-language summary. This is a
    read-only pass — nothing is archived and no profile data is exposed.
    """
    text = payload.raw_text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="raw_text is required")
    understanding = understand_instruction(text, context=payload.context)
    spec = understanding.to_task_spec()
    spec.pop("profile_evidence", None)
    return spec

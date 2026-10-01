"""Data access for the user instruction trace archive.

Writes are deduplicated near the sink: the same instruction re-sent inside the
dedup window folds into the existing row instead of appending a second copy, so
retries and client-side repeats cannot bloat the archive. Compression is
incremental and non-destructive — a summarised batch keeps every original row
and only records the link to the record that absorbed it.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.models_instruction_traces import (
    InstructionSource,
    InstructionTrace,
)

DEFAULT_DEDUP_WINDOW_SECONDS = 300


def compute_text_hash(raw_text: str) -> str:
    """Return the stable digest used to recognise a repeated instruction."""
    return hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


def estimate_token_count(raw_text: str) -> int:
    """Cheap local token estimate used to drive compression decisions."""
    ascii_chars = sum(1 for ch in raw_text if ord(ch) < 128)
    wide_chars = len(raw_text) - ascii_chars
    return (ascii_chars + 3) // 4 + wide_chars


def _window_start(now: datetime, window_seconds: int) -> datetime:
    return now - timedelta(seconds=window_seconds)


def _apply_scope(
    stmt: Select[tuple[InstructionTrace]],
    *,
    session_id: str | None,
    user_id: str | None,
) -> Select[tuple[InstructionTrace]]:
    """Restrict a select to one session and/or one user when given."""
    if session_id is not None:
        stmt = stmt.where(InstructionTrace.session_id == session_id)
    if user_id is not None:
        stmt = stmt.where(InstructionTrace.user_id == user_id)
    return stmt


async def find_duplicate(
    db: AsyncSession,
    *,
    text_hash: str,
    session_id: str | None = None,
    user_id: str | None = None,
    window_seconds: int = DEFAULT_DEDUP_WINDOW_SECONDS,
    now: datetime | None = None,
) -> InstructionTrace | None:
    """Return a recent identical instruction inside the dedup window, if any."""
    if window_seconds <= 0:
        return None
    reference = now or datetime.now(UTC).replace(tzinfo=None)
    stmt = select(InstructionTrace).where(
        InstructionTrace.text_hash == text_hash,
        InstructionTrace.created_at >= _window_start(reference, window_seconds),
    )
    stmt = _apply_scope(stmt, session_id=session_id, user_id=user_id)
    result = await db.execute(stmt.order_by(InstructionTrace.created_at.desc()).limit(1))
    return result.scalar_one_or_none()


async def create_trace(
    db: AsyncSession,
    payload: dict,
    *,
    dedup_window_seconds: int = DEFAULT_DEDUP_WINDOW_SECONDS,
    token_count: int | None = None,
) -> tuple[InstructionTrace, bool]:
    """Archive one instruction, folding a window-local repeat into the prior row.

    Returns the stored row and whether it was an existing row reused for a
    duplicate. The stored ``raw_text`` is never modified by this path.
    """
    raw_text = payload["raw_text"]
    session_id = payload.get("session_id")
    user_id = payload.get("user_id")
    text_hash = compute_text_hash(raw_text)

    duplicate = await find_duplicate(
        db,
        text_hash=text_hash,
        session_id=session_id,
        user_id=user_id,
        window_seconds=dedup_window_seconds,
    )
    if duplicate is not None:
        if payload.get("intent_summary") and not duplicate.intent_summary:
            duplicate.intent_summary = payload["intent_summary"]
        if payload.get("task_spec") and not duplicate.task_spec:
            duplicate.task_spec = payload["task_spec"]
        await db.flush()
        return duplicate, True

    trace = InstructionTrace(
        session_id=session_id,
        user_id=user_id,
        raw_text=raw_text,
        text_hash=text_hash,
        intent_summary=payload.get("intent_summary"),
        task_spec=payload.get("task_spec"),
        source=str(payload.get("source") or InstructionSource.CHAT.value),
        token_count=(token_count if token_count is not None else estimate_token_count(raw_text)),
    )
    db.add(trace)
    await db.flush()
    return trace, False


async def create_traces_bulk(
    db: AsyncSession,
    payloads: Iterable[dict],
    *,
    dedup_window_seconds: int = DEFAULT_DEDUP_WINDOW_SECONDS,
) -> tuple[list[InstructionTrace], int]:
    """Archive a batch of instructions, deduplicating within the batch too."""
    stored: list[InstructionTrace] = []
    deduped = 0
    seen_hashes: set[str] = set()
    for payload in payloads:
        text_hash = compute_text_hash(payload["raw_text"])
        already_seen = text_hash in seen_hashes
        seen_hashes.add(text_hash)
        if already_seen and dedup_window_seconds > 0:
            deduped += 1
            continue
        trace, was_duplicate = await create_trace(
            db, payload, dedup_window_seconds=dedup_window_seconds
        )
        if was_duplicate:
            deduped += 1
            continue
        stored.append(trace)
    return stored, deduped


async def get_trace(db: AsyncSession, trace_id: str) -> InstructionTrace | None:
    return await db.get(InstructionTrace, trace_id)


async def list_by_session(
    db: AsyncSession,
    session_id: str,
    *,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[InstructionTrace]:
    """Return instructions issued during one session, newest first."""
    result = await db.execute(
        select(InstructionTrace)
        .where(InstructionTrace.session_id == session_id)
        .order_by(InstructionTrace.created_at.desc(), InstructionTrace.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


async def list_by_user(
    db: AsyncSession,
    user_id: str,
    *,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[InstructionTrace]:
    """Return every instruction ever issued by one user, newest first."""
    result = await db.execute(
        select(InstructionTrace)
        .where(InstructionTrace.user_id == user_id)
        .order_by(InstructionTrace.created_at.desc(), InstructionTrace.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


async def list_traces(
    db: AsyncSession,
    *,
    session_id: str | None = None,
    user_id: str | None = None,
    is_archived: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[InstructionTrace]:
    """Return a filtered page of instructions, newest first."""
    stmt = select(InstructionTrace)
    stmt = _apply_scope(stmt, session_id=session_id, user_id=user_id)
    if is_archived is not None:
        stmt = stmt.where(InstructionTrace.is_archived.is_(is_archived))
    result = await db.execute(
        stmt.order_by(
            InstructionTrace.created_at.desc(),
            InstructionTrace.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


async def count_traces(
    db: AsyncSession,
    *,
    session_id: str | None = None,
    user_id: str | None = None,
    is_archived: bool | None = None,
) -> int:
    """Count instructions matching the same filters as :func:`list_traces`."""
    stmt = select(func.count()).select_from(InstructionTrace)
    stmt = _apply_scope(stmt, session_id=session_id, user_id=user_id)
    if is_archived is not None:
        stmt = stmt.where(InstructionTrace.is_archived.is_(is_archived))
    result = await db.execute(stmt)
    return int(result.scalar_one())


async def list_unarchived(
    db: AsyncSession,
    *,
    session_id: str | None = None,
    user_id: str | None = None,
    limit: int = 100,
) -> Sequence[InstructionTrace]:
    """Return instructions still eligible for compression, oldest first."""
    stmt = select(InstructionTrace).where(InstructionTrace.is_archived.is_(False))
    stmt = _apply_scope(stmt, session_id=session_id, user_id=user_id)
    result = await db.execute(
        stmt.order_by(InstructionTrace.created_at.asc(), InstructionTrace.id.asc()).limit(limit)
    )
    return result.scalars().all()


async def mark_archived(
    db: AsyncSession,
    trace_ids: Sequence[str],
    *,
    compressed_into_id: str | None = None,
) -> int:
    """Soft-archive instructions, keeping every row and its raw text intact."""
    ids = [tid for tid in trace_ids if tid]
    if not ids:
        return 0
    values: dict = {"is_archived": True, "updated_at": datetime.now(UTC).replace(tzinfo=None)}
    if compressed_into_id is not None:
        values["compressed_into_id"] = compressed_into_id
    result = await db.execute(
        update(InstructionTrace).where(InstructionTrace.id.in_(ids)).values(**values)
    )
    return int(result.rowcount or 0)


async def compress_into_summary(
    db: AsyncSession,
    trace_ids: Sequence[str],
    *,
    summary: str,
    task_spec: dict | None = None,
    source: InstructionSource = InstructionSource.API,
) -> InstructionTrace:
    """Fold old instructions into one new summary row without losing originals.

    The summary row is inserted first, then every source row is soft-marked with
    ``compressed_into_id`` pointing at it. No row is deleted, so the verbatim
    ``raw_text`` of each original instruction stays queryable forever.
    """
    ids = [tid for tid in trace_ids if tid]
    if not ids:
        raise ValueError("compress_into_summary requires at least one trace id")

    source_rows = (
        (await db.execute(select(InstructionTrace).where(InstructionTrace.id.in_(ids))))
        .scalars()
        .all()
    )
    if not source_rows:
        raise ValueError("no instruction traces matched the compression request")

    total_tokens = sum(row.token_count for row in source_rows)
    summary_row = InstructionTrace(
        session_id=source_rows[0].session_id,
        user_id=source_rows[0].user_id,
        raw_text=summary,
        text_hash=compute_text_hash(summary),
        intent_summary=summary,
        task_spec=task_spec,
        goal_preserved=all(row.goal_preserved for row in source_rows) if source_rows else False,
        source=str(source),
        token_count=total_tokens,
    )
    db.add(summary_row)
    await db.flush()

    await mark_archived(db, ids, compressed_into_id=summary_row.id)
    await db.flush()
    return summary_row

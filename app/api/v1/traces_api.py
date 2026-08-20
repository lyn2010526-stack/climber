"""Trace viewing endpoints.

Split out of the former monolithic generic API module (pure move refactor).
Routes are registered with and without a trailing slash because the app runs
with redirect_slashes=False.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.auth import get_current_user
from app.storage import async_session
from app.storage.models_traces import TraceSpanRecord

router = APIRouter(dependencies=[Depends(get_current_user)])
logger = structlog.get_logger()

# ─── Traces ─────────────────────────────────────────────────────────────────

@router.get("/traces")
@router.get("/traces/")
async def list_traces(limit: int = 100) -> list[dict[str, Any]]:
    async with async_session() as db:
        roots = (
            await db.execute(
                select(TraceSpanRecord)
                .where(TraceSpanRecord.parent_id.is_(None))
                .order_by(TraceSpanRecord.started_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        if not roots:
            return []
        trace_ids = [r.trace_id for r in roots]
        spans = (
            await db.execute(
                select(TraceSpanRecord).where(TraceSpanRecord.trace_id.in_(trace_ids))
            )
        ).scalars().all()
        agg: dict[str, dict[str, Any]] = {}
        for s in spans:
            a = agg.setdefault(
                s.trace_id,
                {"span_count": 0, "error_count": 0, "duration_ms": 0.0, "tokens_used": 0},
            )
            a["span_count"] += 1
            if s.status == "error":
                a["error_count"] += 1
            a["duration_ms"] += s.duration_ms or 0
            a["tokens_used"] += s.tokens_used or 0
        result: list[dict[str, Any]] = []
        for r in roots:
            a = agg.get(
                r.trace_id,
                {
                    "span_count": 1,
                    "error_count": 1 if r.status == "error" else 0,
                    "duration_ms": r.duration_ms or 0,
                    "tokens_used": r.tokens_used or 0,
                },
            )
            result.append(
                {
                    "trace_id": r.trace_id,
                    "name": r.name,
                    "kind": r.kind,
                    "status": r.status,
                    "started_at": r.started_at.isoformat() if r.started_at else None,
                    "span_count": a["span_count"],
                    "error_count": a["error_count"],
                    "duration_ms": a["duration_ms"],
                    "tokens_used": a["tokens_used"],
                }
            )
        return result


@router.get("/traces/{trace_id}")
async def get_trace(trace_id: str) -> dict[str, Any]:
    async with async_session() as db:
        rows = (
            await db.execute(
                select(TraceSpanRecord)
                .where(TraceSpanRecord.trace_id == trace_id)
                .order_by(TraceSpanRecord.started_at)
            )
        ).scalars().all()
        if not rows:
            raise HTTPException(status_code=404, detail="Trace not found")
        spans = [s.to_dict() for s in rows]
        total_duration = sum(s.duration_ms or 0 for s in rows)
        total_tokens = sum(s.tokens_used or 0 for s in rows)
        error_count = sum(1 for s in rows if s.status == "error")
        llm_calls = sum(1 for s in rows if s.kind == "llm_call")
        tool_calls = sum(1 for s in rows if s.kind == "tool_call")
        root = next((s for s in rows if s.parent_id is None), rows[0])
        return {
            "trace_id": trace_id,
            "name": root.name,
            "kind": root.kind,
            "status": root.status,
            "started_at": root.started_at.isoformat() if root.started_at else None,
            "spans": spans,
            "stats": {
                "trace_id": trace_id,
                "total_spans": len(spans),
                "total_duration_ms": round(total_duration, 2),
                "total_tokens": int(total_tokens),
                "error_count": error_count,
                "llm_calls": llm_calls,
                "tool_calls": tool_calls,
            },
        }

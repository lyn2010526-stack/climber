"""Trace API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.storage import async_session
from app.storage.models_platform import Trace

router = APIRouter()


@router.get("/traces")
@router.get("/traces/")
async def list_traces(limit: int = 100) -> list[dict[str, Any]]:
    async with async_session() as db:
        rows = (await db.execute(select(Trace).order_by(Trace.created_at.desc()).limit(limit))).scalars().all()
        return [
            {
                "id": t.id,
                "session_id": t.session_id,
                "trace_type": t.trace_type,
                "name": t.name,
                "status": t.status,
                "duration_ms": t.duration_ms,
                "tokens_used": t.tokens_used,
                "error": t.error,
                "spans": t.spans or [],
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in rows
        ]


@router.get("/traces/{trace_id}")
async def get_trace(trace_id: str) -> dict[str, Any]:
    async with async_session() as db:
        t = (await db.execute(select(Trace).where(Trace.id == trace_id))).scalar_one_or_none()
        if t is None:
            raise HTTPException(status_code=404, detail="Trace not found")
        return {
            "id": t.id,
            "session_id": t.session_id,
            "trace_type": t.trace_type,
            "name": t.name,
            "status": t.status,
            "input_data": t.input_data,
            "output_data": t.output_data,
            "spans": t.spans or [],
            "duration_ms": t.duration_ms,
            "tokens_used": t.tokens_used,
            "error": t.error,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }

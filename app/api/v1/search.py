"""Search API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from sqlalchemy import select

from app.storage import async_session
from app.storage.models_platform import DocumentChunk

router = APIRouter()


@router.get("/search")
@router.get("/search/")
async def search_documents(q: str = "", limit: int = 20) -> list[dict[str, Any]]:
    if not q:
        return []
    async with async_session() as db:
        pattern = f"%{q}%"
        rows = (await db.execute(select(DocumentChunk).where(DocumentChunk.content.ilike(pattern)).order_by(DocumentChunk.created_at.desc()).limit(limit))).scalars().all()
        return [{"id": c.id, "document_id": c.document_id, "content": c.content, "chunk_index": c.chunk_index, "score": 0.0, "created_at": c.created_at.isoformat() if c.created_at else ""} for c in rows]

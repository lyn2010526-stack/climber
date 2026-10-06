"""Memory-archive endpoints — sidecars, session archives and scope retrieval.

Exposes the memory-archive subsystem without changing any existing API
contract: L0/L1 sidecar refresh and reads, session archive creation and reads,
directory-scoped retrieval, and the token-cheap context bundle.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.core.auth_manager import require_scopes
from app.core.memory_archive import (
    DirectoryRetriever,
    MemoryContextBypass,
    MemorySidecarService,
    SessionArchiveService,
    memory_context_bypass,
)

router = APIRouter(prefix="/memory", tags=["memory-archive"])

_archiver = SessionArchiveService()
_sidecars = MemorySidecarService()
_retriever = DirectoryRetriever()
_bypass: MemoryContextBypass = memory_context_bypass


class ArchiveRequest(BaseModel):
    session_id: str
    messages: list[dict[str, Any]]
    title: str | None = None
    agent_id: str | None = None


class SidecarEntry(BaseModel):
    path: str
    content: str


class SidecarRequest(BaseModel):
    entries: list[SidecarEntry] = Field(default_factory=list)


@router.post("/archives")
async def create_archive(
    payload: ArchiveRequest,
    user_id: str = Depends(get_current_user),
    _auth: dict[str, Any] = Depends(require_scopes("write")),
) -> dict[str, Any]:
    """Archive a finished session and extract its long-term memories."""
    try:
        return await _archiver.archive(
            user_id,
            payload.session_id,
            payload.messages,
            title=payload.title,
            agent_id=payload.agent_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/archives/{archive_id}")
async def get_archive(
    archive_id: str,
    user_id: str = Depends(get_current_user),
) -> dict[str, Any]:
    """Read one structured session archive."""
    row = await _archiver.get(user_id, archive_id)
    if row is None:
        raise HTTPException(status_code=404, detail="archive not found")
    return row


@router.get("/archives")
async def list_archives(
    session_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    user_id: str = Depends(get_current_user),
) -> dict[str, Any]:
    """List archives for a session, newest first."""
    rows = await _archiver.list_by_session(user_id, session_id, limit=limit)
    return {"total": len(rows), "archives": rows}


@router.post("/sidecars/{scope:path}")
async def refresh_sidecars(
    scope: str,
    payload: SidecarRequest,
    user_id: str = Depends(get_current_user),
    _auth: dict[str, Any] = Depends(require_scopes("write")),
) -> dict[str, Any]:
    """Generate and persist L0/L1 sidecars for a memory directory scope."""
    try:
        bundle = await _sidecars.summarize_directory(
            user_id,
            scope,
            [{"path": entry.path, "content": entry.content} for entry in payload.entries],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return bundle.to_dict()


@router.get("/sidecars/{scope:path}")
async def get_sidecars(
    scope: str,
    level: int | None = Query(default=None, ge=0, le=2),
    user_id: str = Depends(get_current_user),
) -> dict[str, Any]:
    """Read L0/L1 sidecars for a scope (optionally one level)."""
    try:
        pair = await _sidecars.read_pair(user_id, scope)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if level is None:
        records = [row for row in pair if row is not None]
    elif level in (0, 1):
        sidecar = pair[level]
        records = [sidecar] if sidecar is not None else []
    else:
        records = []
    return {
        "scope": scope,
        "records": [
            {
                "id": row.id,
                "level": row.level,
                "scope": row.scope,
                "body": row.body,
                "generated_by": row.generated_by,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in records
        ],
    }


@router.get("/search")
async def search_scope(
    scope: str,
    query: str,
    level: int | None = Query(default=None, ge=0, le=2),
    top_k: int = Query(default=5, ge=1, le=20),
    user_id: str = Depends(get_current_user),
) -> dict[str, Any]:
    """Directory-scoped semantic retrieval (no whole-index scan)."""
    try:
        return await _retriever.search(user_id, scope, query, level=level, top_k=top_k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/context-bundle")
async def context_bundle(
    query: str = "",
    session_id: str = "",
    scopes: str = "",
    include_l1: bool = False,
    user_id: str = Depends(get_current_user),
) -> dict[str, Any]:
    """Token-cheap summary bundle a hook may attach to the conversation."""
    selected = tuple(s.strip() for s in scopes.split(",") if s.strip()) or None
    bundle = await _bypass.build(
        user_id,
        query,
        scopes=selected,
        include_l1=include_l1,
    )
    bundle["session_id"] = session_id
    return bundle

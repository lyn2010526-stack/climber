"""Session CRUD endpoints."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, func, select

from app.core.auth import get_current_user
from app.storage import async_session
from app.storage.database import Message as MessageModel
from app.storage.database import Session as SessionModel

router = APIRouter()


class SessionCreate(BaseModel):
    title: str | None = None
    agent_id: str | None = None
    model_settings: dict[str, Any] | None = None


class SessionOut(BaseModel):
    id: str
    title: str | None
    status: str
    created_at: str
    updated_at: str


class SessionPage(BaseModel):
    items: list[SessionOut]
    total: int
    limit: int
    offset: int


class MessageOut(BaseModel):
    id: str
    role: str
    content: str | None
    tool_name: str | None
    created_at: str


# ─── TTL cache for session list (keyed by user_id) ───────────────────────────

_session_cache: dict[str, tuple[list[dict], float]] = {}
_SESSION_CACHE_TTL = 30.0


# ─── Per-key detail cache for individual sessions ───────────────────────────

_session_detail_cache: dict[str, tuple[dict, float]] = {}
_SESSION_DETAIL_TTL = 30.0


def _get_cached_session(session_id: str, user_id: str) -> dict | None:
    """Return cached session detail or None."""
    entry = _session_detail_cache.get(session_id)
    if entry is not None:
        data, ts = entry
        if time.monotonic() - ts < _SESSION_DETAIL_TTL:
            return data
        del _session_detail_cache[session_id]
    return None


def _set_cached_session(session_id: str, data: dict) -> None:
    _session_detail_cache[session_id] = (data, time.monotonic())


def _invalidate_session(session_id: str) -> None:
    _session_detail_cache.pop(session_id, None)


async def _cached_list_sessions(user_id: str) -> list[SessionOut]:
    entry = _session_cache.get(user_id)
    if entry is not None:
        rows_data, cached_at = entry
        if time.monotonic() - cached_at < _SESSION_CACHE_TTL:
            return [SessionOut(**r) for r in rows_data]

    async with async_session() as session:
        result = await session.execute(
            select(SessionModel)
            .where(SessionModel.user_id == user_id)
            .order_by(SessionModel.created_at.desc())
        )
        rows = result.scalars().all()
        out = [
            SessionOut(
                id=r.id,
                title=r.title,
                status=r.status,
                created_at=r.created_at.isoformat() if r.created_at else "",
                updated_at=r.updated_at.isoformat() if r.updated_at else "",
            )
            for r in rows
        ]
    _session_cache[user_id] = ([r.model_dump() for r in out], time.monotonic())
    return out


@router.get("/", response_model=list[SessionOut])
async def list_sessions_with_slash(user_id: str = Depends(get_current_user)) -> list[SessionOut]:
    return await _cached_list_sessions(user_id)


@router.get("", response_model=list[SessionOut])
async def list_sessions_no_slash(user_id: str = Depends(get_current_user)) -> list[SessionOut]:
    return await _cached_list_sessions(user_id)


@router.post("/", response_model=dict)
async def create_session_with_slash(
    payload: SessionCreate,
    user_id: str = Depends(get_current_user),
) -> dict:
    async with async_session() as session:
        row = SessionModel(
            title=payload.title or "New Session",
            status="idle",
            agent_id=payload.agent_id or None,
            user_id=user_id,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        _session_cache.pop(user_id, None)
        return {"id": row.id, "session_id": row.id, "title": row.title, "status": row.status}



@router.post("", response_model=dict)
async def create_session_no_slash(
    payload: SessionCreate,
    user_id: str = Depends(get_current_user),
) -> dict:
    return await create_session_with_slash(payload, user_id)


@router.post("/create", response_model=dict)
async def create_session_legacy(
    payload: SessionCreate,
    user_id: str = Depends(get_current_user),
) -> dict:
    async with async_session() as session:
        row = SessionModel(
            title=payload.title or "New Session",
            status="idle",
            agent_id=(payload.agent_id or None),
            user_id=user_id,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return {"id": row.id, "session_id": row.id}


class MessagesResponse(BaseModel):
    messages: list[MessageOut]


@router.get("/{session_id}/messages", response_model=MessagesResponse)
async def get_session_messages(session_id: str, user_id: str = Depends(get_current_user)) -> dict:
    async with async_session() as db:
        # Single query: verify ownership then fetch messages in one transaction
        result = await db.execute(
            select(SessionModel.id)
            .where(SessionModel.id == session_id, SessionModel.user_id == user_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Session not found")
        msg_result = await db.execute(
            select(MessageModel)
            .where(MessageModel.session_id == session_id)
            .order_by(MessageModel.created_at.asc())
        )
        rows = msg_result.scalars().all()
        messages = [
            MessageOut(
                id=r.id,
                role=r.role,
                content=r.content,
                tool_name=r.tool_name,
                created_at=r.created_at.isoformat() if r.created_at else "",
            )
            for r in rows
        ]
        return {"messages": messages}


@router.post("/{session_id}/clear")
async def clear_session(session_id: str, user_id: str = Depends(get_current_user)) -> dict:
    from app.core.agent_engine import get_engine
    from app.storage.models_feedback import Feedback

    async with async_session() as db:
        result = await db.execute(
            select(SessionModel).where(SessionModel.id == session_id, SessionModel.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")
        msg_ids = (
            await db.execute(select(MessageModel.id).where(MessageModel.session_id == session_id))
        ).scalars().all()
        if msg_ids:
            await db.execute(delete(Feedback).where(Feedback.message_id.in_(msg_ids)))
        await db.execute(delete(MessageModel).where(MessageModel.session_id == session_id))
        await db.commit()
        _invalidate_session(session_id)
    engine = get_engine()
    engine._session_locks.pop(session_id, None)
    return {"status": "cleared"}


@router.get("/{session_id}")
async def get_session(session_id: str, user_id: str = Depends(get_current_user)) -> dict:
    cached = _get_cached_session(session_id, user_id)
    if cached is not None:
        return cached

    async with async_session() as db:
        result = await db.execute(
            select(SessionModel).where(SessionModel.id == session_id, SessionModel.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")
        data = {
            "id": row.id,
            "title": row.title,
            "status": row.status,
            "agent_id": row.agent_id,
            "created_at": row.created_at.isoformat() if row.created_at else "",
            "updated_at": row.updated_at.isoformat() if row.updated_at else "",
        }
    _set_cached_session(session_id, data)
    return data


@router.delete("/{session_id}")
async def delete_session(session_id: str, user_id: str = Depends(get_current_user)) -> dict:
    from app.storage.database import Turn, UsageLog
    from app.storage.models_cost import CostRecord
    from app.storage.models_feedback import Feedback

    async with async_session() as db:
        result = await db.execute(
            select(SessionModel).where(SessionModel.id == session_id, SessionModel.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")
        msg_ids = (
            await db.execute(select(MessageModel.id).where(MessageModel.session_id == session_id))
        ).scalars().all()
        if msg_ids:
            await db.execute(delete(Feedback).where(Feedback.message_id.in_(msg_ids)))
        await db.execute(delete(MessageModel).where(MessageModel.session_id == session_id))
        await db.execute(delete(Turn).where(Turn.session_id == session_id))
        await db.execute(delete(UsageLog).where(UsageLog.session_id == session_id))
        await db.execute(delete(CostRecord).where(CostRecord.session_id == session_id))
        await db.delete(row)
        await db.commit()
        _invalidate_session(session_id)
        _session_cache.pop(user_id, None)
    from app.core.agent_engine import get_engine
    engine = get_engine()
    engine._session_locks.pop(session_id, None)
    return {"ok": True}


class CheckpointRequest(BaseModel):
    messages: list[dict[str, Any]]
    iteration: int
    status: str = "active"
    metadata: dict[str, Any] | None = None


class ForkRequest(BaseModel):
    new_session_id: str | None = None


@router.post("/{session_id}/checkpoint")
async def save_checkpoint(session_id: str, body: CheckpointRequest) -> dict:
    from app.core.session_manager import SessionManager
    mgr = SessionManager()
    mgr.save_checkpoint(
        session_id=session_id,
        messages=body.messages,
        iteration=body.iteration,
        status=body.status,
        metadata=body.metadata,
    )
    return {"status": "saved", "session_id": session_id}


@router.get("/{session_id}/checkpoint")
async def get_latest_checkpoint(session_id: str) -> dict:
    from app.core.session_manager import SessionManager
    mgr = SessionManager()
    checkpoint = mgr.get_latest_checkpoint(session_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail="No checkpoints found")
    return checkpoint


@router.get("/{session_id}/history")
async def get_checkpoint_history(session_id: str) -> dict:
    from app.core.session_manager import SessionManager
    mgr = SessionManager()
    history = mgr.get_checkpoint_history(session_id)
    return {"session_id": session_id, "checkpoints": history}


@router.post("/{session_id}/fork")
async def fork_session(session_id: str, body: ForkRequest) -> dict:
    from app.core.session_manager import SessionManager
    mgr = SessionManager()
    try:
        new_id = mgr.fork_session(session_id, body.new_session_id)
        return {"session_id": new_id, "status": "forked"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.post("/{session_id}/resume")
async def resume_session(session_id: str) -> dict:
    from app.core.session_manager import SessionManager
    mgr = SessionManager()
    state = mgr.resume_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    return state

"""Session CRUD endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.storage import async_session
from app.storage.database import Session as SessionModel
from app.storage.database import Message as MessageModel

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


@router.get("/", response_model=list[SessionOut])
async def list_sessions_with_slash() -> list[SessionOut]:
    async with async_session() as session:
        result = await session.execute(select(SessionModel).order_by(SessionModel.created_at.desc()))
        rows = result.scalars().all()
        return [
            SessionOut(
                id=r.id,
                title=r.title,
                status=r.status,
                created_at=r.created_at.isoformat() if r.created_at else "",
                updated_at=r.updated_at.isoformat() if r.updated_at else "",
            )
            for r in rows
        ]


@router.get("", response_model=list[SessionOut])
async def list_sessions_no_slash() -> list[SessionOut]:
    return await list_sessions_with_slash()


@router.post("/", response_model=dict)
async def create_session_with_slash(payload: SessionCreate) -> dict:
    async with async_session() as session:
        row = SessionModel(title=payload.title or "New Session", status="idle", agent_id=payload.agent_id or "", user_id=getattr(payload, 'user_id', None) or "default-user")
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return {"id": row.id, "session_id": row.id, "title": row.title, "status": row.status}



@router.post("", response_model=dict)
async def create_session_no_slash(payload: SessionCreate) -> dict:
    return await create_session_with_slash(payload)


@router.post("/create", response_model=dict)
async def create_session_legacy(payload: SessionCreate) -> dict:
    async with async_session() as session:
        row = SessionModel(title=payload.title or "New Session", status="idle", agent_id=payload.agent_id or "", user_id=getattr(payload, 'user_id', None) or "default-user")
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return {"id": row.id, "session_id": row.id}


class MessagesResponse(BaseModel):
    messages: list[MessageOut]


@router.get("/{session_id}/messages", response_model=MessagesResponse)
async def get_session_messages(session_id: str) -> dict:
    async with async_session() as session:
        result = await session.execute(
            select(MessageModel).where(MessageModel.session_id == session_id).order_by(MessageModel.created_at.asc())
        )
        rows = result.scalars().all()
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
async def clear_session(session_id: str) -> dict:
    async with async_session() as session:
        from sqlalchemy import delete
        await session.execute(delete(MessageModel).where(MessageModel.session_id == session_id))
        await session.commit()
    return {"status": "cleared"}


@router.get("/{session_id}")
async def get_session(session_id: str) -> dict:
    async with async_session() as session:
        result = await session.execute(select(SessionModel).where(SessionModel.id == session_id))
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")
        return {
            "id": row.id,
            "title": row.title,
            "status": row.status,
            "agent_id": row.agent_id,
            "created_at": row.created_at.isoformat() if row.created_at else "",
            "updated_at": row.updated_at.isoformat() if row.updated_at else "",
        }


@router.delete("/{session_id}")
async def delete_session(session_id: str) -> dict:
    async with async_session() as session:
        result = await session.execute(select(SessionModel).where(SessionModel.id == session_id))
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")
        await session.delete(row)
        await session.commit()
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
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{session_id}/resume")
async def resume_session(session_id: str) -> dict:
    from app.core.session_manager import SessionManager
    mgr = SessionManager()
    state = mgr.resume_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    return state

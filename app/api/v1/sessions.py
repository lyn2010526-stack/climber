"""Session CRUD endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.core.auth import get_current_user
from app.storage import async_session
from app.storage.database import Agent as AgentModel
from app.storage.database import ApiKey as ApiKeyModel
from app.storage.database import Message as MessageModel
from app.storage.database import Session as SessionModel

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_CHECKPOINT_KEY = "_checkpoints"


def _clean_model_settings(settings: dict[str, Any] | None) -> dict[str, Any]:
    if not settings:
        return {}
    cleaned = {}
    for key in ("provider", "model_id", "base_url", "credential_id"):
        value = settings.get(key)
        if value is None:
            continue
        if not isinstance(value, str) or (key == "credential_id" and not value.strip()):
            raise HTTPException(422, detail=f"Invalid model_settings.{key}")
        if value.strip():
            cleaned[key] = value.strip()
    return cleaned


async def resolve_model_credential(
    db: AsyncSession, user_id: str, settings: dict[str, Any],
) -> ApiKeyModel | None:
    """Resolve an explicit credential identically at creation and every chat turn."""
    credential_id = settings.get("credential_id")
    if not credential_id:
        return None
    row = await db.scalar(select(ApiKeyModel).where(
        ApiKeyModel.id == credential_id, ApiKeyModel.user_id == user_id,
        ApiKeyModel.is_active.is_(True),
    ))
    if row is None:
        raise HTTPException(404, detail="Selected model credential is unavailable or revoked")
    if settings.get("provider") and settings["provider"] != row.provider:
        raise HTTPException(422, detail="Selected credential does not match model provider")
    if not settings.get("model_id"):
        raise HTTPException(422, detail="A model_id is required with credential_id")
    settings["provider"] = row.provider
    # Endpoint and key are resolved from this record at execution time.
    settings.pop("base_url", None)
    return row


def _session_effective_model(row: SessionModel, agent: AgentModel | None) -> dict[str, Any]:
    settings = row.model_settings or {}
    provider = settings.get("provider")
    model_id = settings.get("model_id")
    if (not provider or not model_id) and agent is not None:
        provider = provider or agent.provider
        model_id = model_id or agent.model_id
    return {"provider": provider, "model_id": model_id}


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
    provider: str | None = None
    model_id: str | None = None


class SessionPage(BaseModel):
    items: list[SessionOut]
    total: int
    limit: int
    offset: int


class MessageOut(BaseModel):
    id: str
    role: str
    content: str | None
    tool_call_id: str | None
    tool_calls: list[dict[str, Any]]
    tool_name: str | None
    created_at: str


@router.get("/", response_model=list[SessionOut])
async def list_sessions_with_slash(user_id: str = Depends(get_current_user)) -> list[SessionOut]:
    async with async_session() as session:
        result = await session.execute(
            select(SessionModel)
            .where(SessionModel.user_id == user_id)
            .order_by(SessionModel.created_at.desc())
        )
        rows = result.scalars().all()
        agent_ids = {r.agent_id for r in rows if r.agent_id}
        agents: dict[str, AgentModel] = {}
        if agent_ids:
            agent_result = await session.execute(
                select(AgentModel).where(AgentModel.id.in_(agent_ids))
            )
            agents = {a.id: a for a in agent_result.scalars().all()}
        return [
            SessionOut(
                id=r.id,
                title=r.title,
                status=r.status,
                created_at=r.created_at.isoformat() if r.created_at else "",
                updated_at=r.updated_at.isoformat() if r.updated_at else "",
                **_session_effective_model(r, agents.get(r.agent_id or "")),
            )
            for r in rows
        ]


@router.get("", response_model=list[SessionOut])
async def list_sessions_no_slash(user_id: str = Depends(get_current_user)) -> list[SessionOut]:
    return await list_sessions_with_slash(user_id)


@router.post("/", response_model=dict)
async def create_session_with_slash(
    payload: SessionCreate,
    user_id: str = Depends(get_current_user),
) -> dict:
    async with async_session() as session:
        agent = None
        if payload.agent_id:
            agent = (
                await session.execute(select(AgentModel).where(
                    AgentModel.id == payload.agent_id, AgentModel.user_id == user_id,
                ))
            ).scalar_one_or_none()
            if agent is None:
                raise HTTPException(404, detail="Agent not found")
        model_settings = _clean_model_settings(payload.model_settings)
        await resolve_model_credential(session, user_id, model_settings)
        row = SessionModel(
            title=payload.title or "New Session",
            status="idle",
            agent_id=payload.agent_id or None,
            user_id=user_id,
            model_settings=model_settings,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return {
            "id": row.id,
            "session_id": row.id,
            "title": row.title,
            "status": row.status,
            **_session_effective_model(row, agent),
        }



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
    return await create_session_with_slash(payload, user_id)


class MessagesResponse(BaseModel):
    messages: list[MessageOut]


@router.get("/{session_id}/messages", response_model=MessagesResponse)
async def get_session_messages(session_id: str, user_id: str = Depends(get_current_user)) -> dict:
    async with async_session() as session:
        owner = await session.scalar(
            select(SessionModel).where(
                SessionModel.id == session_id,
                SessionModel.user_id == user_id,
            )
        )
        if owner is None:
            raise HTTPException(status_code=404, detail="Session not found")
        result = await session.execute(
            select(MessageModel).where(MessageModel.session_id == session_id).order_by(MessageModel.created_at.asc())
        )
        rows = result.scalars().all()
        messages = [
            MessageOut(
                id=r.id,
                role=r.role,
                content=r.content,
                tool_call_id=r.tool_call_id,
                tool_calls=r.tool_calls or [],
                tool_name=r.tool_name,
                created_at=r.created_at.isoformat() if r.created_at else "",
            )
            for r in rows
        ]
        return {"messages": messages}


@router.post("/{session_id}/clear")
async def clear_session(session_id: str, user_id: str = Depends(get_current_user)) -> dict:
    async with async_session() as session:
        result = await session.execute(select(SessionModel).where(SessionModel.id == session_id))
        row = result.scalar_one_or_none()
        if not row or (row.user_id and row.user_id != user_id):
            raise HTTPException(status_code=404, detail="Session not found")
        from sqlalchemy import delete
        await session.execute(delete(MessageModel).where(MessageModel.session_id == session_id))
        await session.commit()
    return {"status": "cleared"}


@router.get("/{session_id}")
async def get_session(session_id: str, user_id: str = Depends(get_current_user)) -> dict:
    async with async_session() as session:
        result = await session.execute(select(SessionModel).where(SessionModel.id == session_id))
        row = result.scalar_one_or_none()
        if not row or (row.user_id and row.user_id != user_id):
            raise HTTPException(status_code=404, detail="Session not found")
        return {
            "id": row.id,
            "title": row.title,
            "status": row.status,
            "agent_id": row.agent_id,
            "created_at": row.created_at.isoformat() if row.created_at else "",
            "updated_at": row.updated_at.isoformat() if row.updated_at else "",
            **_session_effective_model(
                row,
                (
                    await session.execute(select(AgentModel).where(AgentModel.id == row.agent_id))
                ).scalar_one_or_none()
                if row.agent_id
                else None,
            ),
        }


@router.delete("/{session_id}")
async def delete_session(session_id: str, user_id: str = Depends(get_current_user)) -> dict:
    async with async_session() as session:
        result = await session.execute(select(SessionModel).where(SessionModel.id == session_id))
        row = result.scalar_one_or_none()
        if not row or (row.user_id and row.user_id != user_id):
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


async def _ensure_owned_session(session_id: str, user_id: str) -> None:
    """Raise 404 unless the session exists and belongs to the given user."""
    async with async_session() as session:
        row = (
            await session.execute(select(SessionModel).where(SessionModel.id == session_id))
        ).scalar_one_or_none()
        if not row or (row.user_id and row.user_id != user_id):
            raise HTTPException(status_code=404, detail="Session not found")


async def _load_owned_session(db: Any, session_id: str, user_id: str) -> SessionModel:
    """Fetch an owned session row within the given session or raise 404."""
    row = (
        await db.execute(select(SessionModel).where(SessionModel.id == session_id))
    ).scalar_one_or_none()
    if not row or (row.user_id and row.user_id != user_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return row


def _load_checkpoints(row: SessionModel) -> list[dict[str, Any]]:
    data = row.context_data or {}
    return list(data.get(_CHECKPOINT_KEY, []))


def _save_checkpoints(row: SessionModel, checkpoints: list[dict[str, Any]]) -> None:
    data = dict(row.context_data or {})
    data[_CHECKPOINT_KEY] = checkpoints
    row.context_data = data


@router.post("/{session_id}/checkpoint")
async def save_checkpoint(
    session_id: str,
    body: CheckpointRequest,
    user_id: str = Depends(get_current_user),
) -> dict:
    async with async_session() as session:
        row = await _load_owned_session(session, session_id, user_id)
        checkpoints = _load_checkpoints(row)
        checkpoint = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "iteration": body.iteration,
            "status": body.status,
            "messages": body.messages or [],
            "metadata": body.metadata or {},
            "created_at": datetime.now(UTC).isoformat(),
        }
        checkpoints.append(checkpoint)
        _save_checkpoints(row, checkpoints[-50:])
        await session.commit()
    return {
        "status": "saved",
        "session_id": session_id,
        "checkpoint_id": checkpoint["id"],
        "total": len(checkpoints[-50:]),
    }


@router.get("/{session_id}/checkpoint")
async def get_latest_checkpoint(session_id: str, user_id: str = Depends(get_current_user)) -> dict:
    async with async_session() as session:
        row = await _load_owned_session(session, session_id, user_id)
        checkpoints = _load_checkpoints(row)
    if not checkpoints:
        raise HTTPException(status_code=404, detail="No checkpoints found")
    return checkpoints[-1]


@router.get("/{session_id}/history")
async def get_checkpoint_history(session_id: str, user_id: str = Depends(get_current_user)) -> dict:
    async with async_session() as session:
        row = await _load_owned_session(session, session_id, user_id)
        checkpoints = _load_checkpoints(row)
    return {"session_id": session_id, "checkpoints": checkpoints}


@router.post("/{session_id}/fork")
async def fork_session(session_id: str, body: ForkRequest, user_id: str = Depends(get_current_user)) -> dict:
    async with async_session() as session:
        source = await _load_owned_session(session, session_id, user_id)
        new_id = body.new_session_id or str(uuid.uuid4())
        existing = (
            await session.execute(select(SessionModel).where(SessionModel.id == new_id))
        ).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(status_code=409, detail="Target session id already exists")
        snapshot = SessionModel(
            id=new_id,
            title=f"{source.title} (fork)" if source.title else "Forked Session",
            agent_id=source.agent_id,
            user_id=user_id,
            status=source.status,
            model_settings=dict(source.model_settings or {}),
            context_data=dict(source.context_data or {}),
            iteration_count=source.iteration_count,
            total_tokens=source.total_tokens,
            working_memory=dict(source.working_memory or {}),
        )
        session.add(snapshot)
        rows = (
            await session.execute(
                select(MessageModel)
                .where(MessageModel.session_id == session_id)
                .order_by(MessageModel.created_at.asc())
            )
        ).scalars().all()
        for msg in rows:
            session.add(
                MessageModel(
                    session_id=new_id,
                    role=msg.role,
                    content=msg.content,
                    tool_call_id=msg.tool_call_id,
                    tool_calls=msg.tool_calls or [],
                    tool_name=msg.tool_name,
                    tokens=msg.tokens,
                    parent_id=None,
                    branch_id=msg.branch_id or "main",
                    children_count=0,
                )
            )
        await session.commit()
    return {"session_id": new_id, "status": "forked"}


@router.post("/{session_id}/resume")
async def resume_session(session_id: str, user_id: str = Depends(get_current_user)) -> dict:
    async with async_session() as session:
        row = await _load_owned_session(session, session_id, user_id)
        checkpoints = _load_checkpoints(row)
        messages = [
            {
                "role": m.role,
                "content": m.content,
                "tool_call_id": m.tool_call_id,
                "tool_calls": m.tool_calls or [],
                "tool_name": m.tool_name,
                "created_at": m.created_at.isoformat() if m.created_at else "",
            }
            for m in (
                await session.execute(
                    select(MessageModel)
                    .where(MessageModel.session_id == session_id)
                    .order_by(MessageModel.created_at.asc())
                )
            )
            .scalars()
            .all()
        ]
    if not checkpoints:
        raise HTTPException(
            status_code=404,
            detail="No checkpoint found to resume from",
        )
    return {
        "session_id": session_id,
        "status": row.status,
        "checkpoint": checkpoints[-1],
        "messages": messages,
        "iteration_count": row.iteration_count,
        "total_tokens": row.total_tokens,
    }

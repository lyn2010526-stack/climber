"""Chat slash-command endpoints: parse, execute, cancel, retry.

Routes:
- ``GET  /chat-commands``                      — palette metadata for the frontend
- ``POST /chat-commands/parse``                — parse preview (validation feedback)
- ``POST /sessions/{session_id}/slash``        — execute one command (SSE when streaming)
- ``POST /sessions/{session_id}/cancel``       — interrupt the running turn
- ``POST /sessions/{session_id}/retry``        — re-run the last user message (SSE)

The slash endpoint mirrors the auth/ownership rules of ``app.api.v1.chat``:
credentials and model bindings are re-resolved from persisted state on every
call, and streaming replies reuse the engine's ``AgentEvent.to_sse()`` frames.
Unmatched input is forwarded to the engine verbatim, exactly like the regular
chat endpoint.
"""

from __future__ import annotations

from copy import copy
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.api.v1.chat import _ChatModelRegistry, _chat_inflight, get_engine
from app.api.v1.sessions import _clean_model_settings, resolve_model_credential
from app.core import AgentEvent, AgentEventType
from app.core.agent_engine import AgentEngine
from app.core.api_key_crypto import decrypt_api_key
from app.core.auth import get_current_user
from app.core.slash import (
    SlashCommandService,
    command_catalog,
    default_registry,
    parse_input,
)
from app.storage import async_session
from app.storage.database import Agent as AgentModel
from app.storage.database import Message as MessageModel
from app.storage.database import Session as SessionModel

# ruff: noqa: SLF001 - engine internals are accessed through the same seams chat.py uses.

router = APIRouter(tags=["chat-commands"])

_registry = default_registry


class SlashRequest(BaseModel):
    message: str


class ParseRequest(BaseModel):
    message: str


def build_service(engine: AgentEngine | None = None) -> SlashCommandService:
    """Build a service bound to the live engine's warm-session map."""

    async def load_session(session_id: str, user_id: str) -> SessionModel | None:
        async with async_session() as db:
            return await db.scalar(select(SessionModel).where(
                SessionModel.id == session_id, SessionModel.user_id == user_id,
            ))

    return SlashCommandService(
        _registry,
        db_factory=async_session,
        load_session=load_session,
        engine_sessions=engine._sessions if engine is not None else {},
    )


def _sse(event: AgentEvent) -> str:
    return event.to_sse()


def _error_event(message: str) -> AgentEvent:
    return AgentEvent(type=AgentEventType.ERROR, data={"error": message})


def _stream_local(events: list[AgentEvent]):
    async def _gen() -> Any:
        for event in events:
            yield _sse(event)

    return StreamingResponse(_gen(), media_type="text/event-stream")


async def _resolve_run_context(session_id: str, user_id: str) -> dict[str, Any]:
    """Resolve ownership + credentials exactly like the chat endpoint does."""
    async with async_session() as db:
        row = await db.scalar(select(SessionModel).where(
            SessionModel.id == session_id, SessionModel.user_id == user_id,
        ))
        if row is None:
            raise HTTPException(404, detail="Session not found")
        agent_id = row.agent_id or ""
        agent = await db.scalar(select(AgentModel).where(
            AgentModel.id == agent_id, AgentModel.user_id == user_id,
        )) if agent_id else None
        if agent_id and agent is None:
            raise HTTPException(404, detail="Agent not found")
        settings = _clean_model_settings(row.model_settings)
        credential = await resolve_model_credential(db, user_id, settings)
        provider = settings.get("provider") or getattr(agent, "provider", None) or "openai"
        model_id = settings.get("model_id") or getattr(agent, "model_id", None) or "gpt-4o-mini"
        system_prompt = getattr(agent, "system_prompt", None) or ""
        tool_ids = list(getattr(agent, "tool_ids", None) or [])
        if credential is not None:
            encrypted_key = credential.api_key_encrypted
            base_url = credential.base_url
        else:
            if agent is None or provider != agent.provider:
                raise HTTPException(422, detail="Select a saved model credential")
            if settings.get("base_url") and settings["base_url"] != agent.base_url:
                raise HTTPException(422, detail="Select a saved credential for this endpoint")
            encrypted_key = agent.api_key_encrypted
            base_url = agent.base_url
        try:
            api_key = decrypt_api_key(encrypted_key or "")
        except ValueError as exc:
            raise HTTPException(422, detail="Model credential cannot be decrypted") from exc
        if not api_key.strip() and provider != "ollama":
            raise HTTPException(422, detail="Model credential has no API key")
    return {
        "provider": provider,
        "model_id": model_id,
        "api_key": api_key,
        "base_url": base_url,
        "system_prompt": system_prompt,
        "tools": tool_ids,
        "agent_id": agent_id,
        "row": row,
    }


def _prepare_engine(context: dict[str, Any], session_id: str, user_id: str) -> AgentEngine:
    """Return a per-request engine copy, mirroring chat.py's warm-session rules."""
    engine = copy(get_engine())
    session = engine._sessions.get(session_id)
    if session is not None and session.user_id != user_id:
        raise HTTPException(403, detail="Forbidden")
    try:
        engine.model_registry = _ChatModelRegistry(
            context["provider"], context["model_id"], context["api_key"], context["base_url"],
        )
    except Exception as exc:
        raise HTTPException(422, detail="Model credential could not be initialized") from exc
    engine._init_reasoning()
    return engine


@router.get("/chat-commands")
async def list_commands() -> dict[str, Any]:
    """Command catalog for the input autocomplete palette."""
    return {"commands": command_catalog(_registry)}


@router.post("/chat-commands/parse")
async def parse_command(request: ParseRequest, user_id: str = Depends(get_current_user)) -> dict[str, Any]:
    """Parse input without executing; the client uses this for live validation."""
    outcome = parse_input(request.message, _registry)
    result: dict[str, Any] = {
        "kind": outcome.kind,
        "raw": outcome.raw,
        "command": outcome.command,
        "args": outcome.args,
        "error": outcome.error,
    }
    if outcome.spec is not None:
        result["usage"] = outcome.spec.usage
        result["streaming"] = outcome.spec.streaming
        result["allowed_while_streaming"] = outcome.spec.allowed_while_streaming
    return result


@router.post("/sessions/{session_id}/cancel")
async def cancel_session_turn(session_id: str, user_id: str = Depends(get_current_user)) -> dict[str, Any]:
    """Interrupt the in-flight turn of this session (cooperative engine stop)."""
    engine = get_engine()
    session = engine._sessions.get(session_id)
    lock = engine._session_locks.get(session_id)
    turn_running = session_id in _chat_inflight or (lock is not None and lock.locked())
    if session is None and not turn_running:
        raise HTTPException(404, detail="No running turn for this session")
    if session is not None and session.user_id != user_id:
        raise HTTPException(403, detail="Forbidden")
    if not turn_running:
        raise HTTPException(409, detail="No running turn to interrupt")
    service = build_service(engine)
    outcome = parse_input("/stop", _registry)
    execution = await service.execute(outcome, session_id=session_id, user_id=user_id, running=True)
    if execution.reply is None or execution.reply.effect != "stop_requested":
        raise HTTPException(409, detail="No running turn to interrupt")
    return {"session_id": session_id, "cancelled": True, "detail": execution.reply.content}


@router.post("/sessions/{session_id}/slash")
async def slash_command(
    session_id: str,
    request: SlashRequest,
    user_id: str = Depends(get_current_user),
):
    """Execute one slash command; unmatched input streams through the engine.

    Replies are always SSE: local commands emit synthetic ``text``/``done``
    frames, ``retry`` and passthrough stream genuine engine events. This keeps
    the client on a single consumption path.
    """
    outcome = parse_input(request.message, _registry)
    if outcome.kind == "passthrough":
        # Nothing intercepted: behave exactly like the regular chat endpoint.
        return await _stream_engine_turn(session_id, user_id, outcome.raw)

    engine = get_engine()
    running = session_id in _chat_inflight
    service = build_service(engine)
    execution = await service.execute(
        outcome, session_id=session_id, user_id=user_id, running=running,
    )

    if execution.kind == "error":
        return _stream_local([_error_event(execution.reply.content if execution.reply else "Command failed")])
    if execution.kind == "passthrough":
        if execution.agent_message is None:
            # /retry: re-run the last persisted user message as a fresh turn.
            return await _retry_last_turn(session_id, user_id)
        return await _stream_engine_turn(session_id, user_id, execution.agent_message)

    reply = execution.reply
    content = reply.content if reply else "Done."
    return _stream_local([
        AgentEvent(type=AgentEventType.TEXT, data={"content": content}),
        AgentEvent(type=AgentEventType.DONE, data={
            "status": "completed",
            "command": outcome.command,
            "effect": reply.effect if reply else None,
            "payload": reply.payload if reply else {},
        }),
    ])


async def _retry_last_turn(session_id: str, user_id: str):
    context = await _resolve_run_context(session_id, user_id)
    async with async_session() as db:
        row = (await db.scalars(
            select(MessageModel).where(
                MessageModel.session_id == session_id,
                MessageModel.role == "user",
            ).order_by(MessageModel.created_at.desc(), MessageModel.id.desc()).limit(1)
        )).first()
    if row is None or not (row.content or "").strip():
        return _stream_local([_error_event("Nothing to retry yet: no previous user message")])
    # /retry re-runs the stored text as a NEW user turn; the original turn's
    # output stays in history for contrast.
    return await _stream_engine_turn(session_id, user_id, row.content, context)


async def _stream_engine_turn(
    session_id: str,
    user_id: str,
    message: str,
    context: dict[str, Any] | None = None,
):
    """Stream one engine turn with chat.py's credential/lock discipline."""
    context = context or await _resolve_run_context(session_id, user_id)
    engine = _prepare_engine(context, session_id, user_id)
    session = engine._sessions.get(session_id)
    lock = engine._session_locks.get(session_id)
    if session_id in _chat_inflight or (lock is not None and lock.locked()):
        return _stream_local([_error_event("Session is already running")])
    is_new_session = session is None
    if session is None:
        session = engine.create_session(
            agent_id=context["agent_id"],
            user_id=user_id,
            provider=context["provider"],
            model_id=context["model_id"],
            api_key=context["api_key"],
            base_url=context["base_url"],
            system_prompt=context["system_prompt"],
            tools=context["tools"],
            session_id=session_id,
        )
    # Rebind after recovery and on every turn so rotation takes effect — the
    # same discipline chat.py applies to warm sessions.
    for name, value in (
        ("provider", context["provider"]),
        ("model_id", context["model_id"]),
        ("api_key", context["api_key"]),
        ("base_url", context["base_url"]),
    ):
        setattr(session, name, value)
        if getattr(session, "session_config", None) is not None:
            setattr(session.session_config, name, value)

    _chat_inflight.add(session_id)

    async def _stream() -> Any:
        try:
            async for event in engine.run(session, message):
                yield _sse(event)
        except Exception:
            yield _sse(_error_event("Model execution failed; verify the selected credential and model"))
        finally:
            _chat_inflight.discard(session_id)

    return StreamingResponse(_stream(), media_type="text/event-stream")

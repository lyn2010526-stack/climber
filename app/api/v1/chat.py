"""Session chat endpoint with SSE streaming."""

# The existing engine exposes canonical state through these integration seams.
# ruff: noqa: SLF001

from __future__ import annotations

from copy import copy
from contextlib import aclosing
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.api.v1.sessions import _clean_model_settings, resolve_model_credential
from app.core import AgentEvent, AgentEventType
from app.core.agent_engine import AgentEngine
from app.core.api_key_crypto import decrypt_api_key
from app.core.auth import get_current_user
from app.core.auth_manager import require_scopes
from app.core.di import resolve as di_resolve
from app.core.recovery import RecoveryManager
from app.models.registry import MODEL_ALIASES, ModelRegistry
from app.models.vision import validate_attachments, validate_images
from app.storage import async_session
from app.storage.database import Agent as AgentModel
from app.storage.database import Session as SessionModel

router = APIRouter()

_engine: AgentEngine | None = None
_chat_inflight: set[str] = set()


class _ChatModelRegistry:
    """Bind chat and reasoning to one verified credential, without shared caches."""

    def __init__(self, provider: str, model_id: str, api_key: str, base_url: str | None):
        self.provider = provider
        self.model_id = model_id
        self._api_key = api_key
        self._base_url = base_url
        self._adapter = ModelRegistry().register_model(model_id, provider, api_key, base_url)

    def get_or_create(
        self, provider: str, model_id: str = "", api_key: str = "", base_url: str | None = None,
    ):
        if not model_id:
            provider, model_id = MODEL_ALIASES.get(
                provider, tuple(provider.split(":", 1)) if ":" in provider
                else (self.provider, provider),
            )
        if (provider, model_id) != (self.provider, self.model_id):
            raise ValueError("Requested model is not bound to the session credential")
        if (api_key and api_key != self._api_key) or (base_url is not None and base_url != self._base_url):
            raise ValueError("Requested credentials do not match the session binding")
        return self._adapter

    def get_default(self):
        return self._adapter

    def get_model(self, provider: str, model_id: str):
        return self.get_or_create(provider, model_id)


def get_engine() -> AgentEngine:
    global _engine
    if _engine is None:
        model_registry = di_resolve("ModelRegistry")
        tool_registry = di_resolve("ToolRegistry")
        _engine = AgentEngine(model_registry=model_registry, tool_registry=tool_registry)
    return _engine


class ChatRequest(BaseModel):
    message: str
    # Optional image references (base64 data URLs or http(s) URLs) for multimodal chat.
    images: list[str] | None = None
    attachments: list[dict[str, Any]] | None = None


@router.post("/{session_id}/chat")
async def chat(
    session_id: str,
    request: ChatRequest,
    user_id: str = Depends(get_current_user),
    _scope_check: None = Depends(require_scopes("write")),
):
    return await _session_stream(session_id, request, user_id)


@router.post("/{session_id}/inputs/start")
async def start_session_inputs(
    session_id: str,
    user_id: str = Depends(get_current_user),
    _scope_check: None = Depends(require_scopes("write")),
):
    return await _session_stream(session_id, ChatRequest(message=""), user_id, queued_only=True)


async def _session_stream(session_id: str, request: ChatRequest, user_id: str, *, queued_only=False):
    try:
        images = validate_images(request.images)
        attachments = validate_attachments(request.attachments)
        if images and attachments:
            raise ValueError("Use images or attachments, not both")
        if images:
            attachments = []
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    # Always resolve persisted ownership and credentials, including warm sessions.
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
            # An Agent key may only be sent to the Agent's configured endpoint.
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

    engine = copy(get_engine())
    session = engine._sessions.get(session_id)
    if session is not None and session.user_id != user_id:
        raise HTTPException(403, detail="Forbidden")
    lock = engine._session_locks.get(session_id)
    if session_id in _chat_inflight or (lock is not None and lock.locked()):
        raise HTTPException(409, detail="Session is already running")
    if queued_only:
        from app.core.engine.input_dispatch import InputDispatchConflict, prepare_dispatch

        try:
            await prepare_dispatch(engine._input_queue, session_id, user_id)
        except InputDispatchConflict as exc:
            raise HTTPException(409, detail=str(exc)) from exc
    try:
        engine.model_registry = _ChatModelRegistry(provider, model_id, api_key, base_url)
    except Exception as exc:
        raise HTTPException(422, detail="Selected model credential could not be initialized") from exc
    adapter = engine.model_registry.get_default()
    if attachments and any(item.kind == "image" for item in attachments) and not adapter.capabilities.vision:
        raise HTTPException(422, detail=f"Model {provider}/{model_id} does not support image attachments")
    if attachments and any(item.kind == "file" for item in attachments) and not adapter.capabilities.file_attachments:
        raise HTTPException(422, detail=f"Model {provider}/{model_id} does not support file attachments")
    engine._init_reasoning()
    # Preflight awaits database I/O; another request may have reserved the stream.
    lock = engine._session_locks.get(session_id)
    if session_id in _chat_inflight or (lock is not None and lock.locked()):
        raise HTTPException(409, detail="Session is already running")
    _chat_inflight.add(session_id)
    is_new_session = session is None
    try:
        if session is None:
            session = engine.create_session(
                agent_id=agent_id, user_id=user_id, provider=provider, model_id=model_id,
                api_key=api_key, base_url=base_url, system_prompt=system_prompt,
                tools=tool_ids, session_id=session_id,
            )
            if not queued_only:
                await RecoveryManager().restore_session(session)
        # Rebind after recovery and on every turn so rotation takes effect.
        for name, value in {
            "provider": provider, "model_id": model_id, "api_key": api_key, "base_url": base_url,
        }.items():
            setattr(session, name, value)
            setattr(session.session_config, name, value)
    except BaseException:
        if is_new_session:
            engine._sessions.pop(session_id, None)
        _chat_inflight.discard(session_id)
        raise

    async def _stream() -> Any:
        try:
            # Only pass the new field when present so engines predating images keep working.
            runner = (
                engine.run_inputs(session) if queued_only else
                engine.run(session, request.message, images=images)
                if images
                else (
                    engine.run(session, request.message, attachments=attachments)
                    if attachments
                    else engine.run(session, request.message)
                )
            )
            async with aclosing(runner):
                async for event in runner:
                    yield event.to_sse()
        except Exception as e:
            import structlog
            structlog.get_logger().error("chat_stream_error", session_id=session_id, error_type=type(e).__name__)
            error_event = AgentEvent(
                type=AgentEventType.ERROR,
                data={"error": "Model execution failed; verify the selected credential and model"},
            )
            yield error_event.to_sse()
            yield AgentEvent(type=AgentEventType.DONE, data={"status": "failed"}).to_sse()
        finally:
            _chat_inflight.discard(session_id)

    return StreamingResponse(_stream(), media_type="text/event-stream")

"""Session chat endpoint with SSE streaming."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core import AgentEvent, AgentEventType
from app.core.agent_engine import AgentEngine
from app.core.api_key_crypto import decrypt_api_key
from app.core.auth import get_current_user
from app.core.di import resolve as di_resolve
from app.storage import async_session
from app.storage.database import Agent as AgentModel
from app.storage.database import ApiKey as ApiKeyModel
from app.storage.database import Session as SessionModel

router = APIRouter()

_engine: AgentEngine | None = None


def get_engine() -> AgentEngine:
    global _engine
    if _engine is None:
        model_registry = di_resolve("ModelRegistry")
        tool_registry = di_resolve("ToolRegistry")
        _engine = AgentEngine(model_registry=model_registry, tool_registry=tool_registry)
    return _engine


class ChatRequest(BaseModel):
    message: str


@router.post("/{session_id}/chat")
async def chat(
    session_id: str,
    request: ChatRequest,
    user_id: str = Depends(get_current_user),
):
    engine = get_engine()
    session = engine._sessions.get(session_id)
    if session is None:
        provider = "openai"
        model_id = "gpt-4o-mini"
        api_key = ""
        base_url = None
        system_prompt = ""
        agent_id = ""
        tool_ids = []
        try:
            async with async_session() as db:
                from sqlalchemy import select
                result = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
                row = result.scalar_one_or_none()
                if not row:
                    raise HTTPException(status_code=404, detail="Session not found")
                if row.user_id and row.user_id != user_id:
                    raise HTTPException(status_code=403, detail="Forbidden")
                agent_id = row.agent_id or ""
                agent_result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
                agent_row = agent_result.scalar_one_or_none()
                if agent_row:
                    provider = agent_row.provider or "openai"
                    model_id = agent_row.model_id or "gpt-4o-mini"
                    base_url = agent_row.base_url
                    system_prompt = agent_row.system_prompt or ""
                    api_key = decrypt_api_key(agent_row.api_key_encrypted or "")
                if not api_key:
                    key_result = await db.execute(
                        select(ApiKeyModel)
                        .where(ApiKeyModel.provider == provider)
                        .where(ApiKeyModel.is_active == True)
                    )
                    key_row = key_result.scalar_one_or_none()
                    if key_row:
                        api_key = decrypt_api_key(key_row.api_key_encrypted or "")
                        if key_row.base_url:
                            base_url = key_row.base_url
                agent_tools = list(getattr(agent_row, "tool_ids", None) or [])
                from app.tools import tool_registry as _chat_tool_registry
                registered = {t.name for t in _chat_tool_registry.list_tools()}
                tool_ids = sorted(set(agent_tools) | registered)
        except HTTPException:
            raise
        except Exception as e:
            import structlog
            structlog.get_logger().warning("chat_session_load_failed", session_id=session_id, error=str(e))
        session = engine.create_session(
            agent_id=agent_id,
            user_id=user_id,
            provider=provider,
            model_id=model_id,
            api_key=api_key,
            base_url=base_url,
            system_prompt=system_prompt,
            tools=tool_ids,
            session_id=session_id,
        )
        engine._sessions[session_id] = session

    if session.user_id and session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    async def _stream() -> Any:
        try:
            async for event in engine.run(session, request.message):
                yield event.to_sse()
        except Exception as e:
            import structlog
            structlog.get_logger().error("chat_stream_error", session_id=session_id, error=str(e), exc_info=True)
            error_event = AgentEvent(
                type=AgentEventType.ERROR,
                data={"error": f"Stream error: {type(e).__name__}: {e!s}"},
            )
            yield error_event.to_sse()

    return StreamingResponse(_stream(), media_type="text/event-stream")

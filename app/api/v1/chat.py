"""Session chat endpoint with SSE streaming using Frame Protocol."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.agent_engine import AgentEngine
from app.core.di import resolve as di_resolve
from app.core.frame import Frame
from sqlalchemy import select

from app.storage import async_session
from app.storage.database import Session as SessionModel
from app.storage.database import Agent as AgentModel
from app.storage.database import ApiKey as ApiKeyModel

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
async def chat(session_id: str, request: ChatRequest):
    engine = get_engine()
    session = engine._sessions.get(session_id)
    if session is None:
        provider = "openai"
        model_id = "gpt-4o"
        api_key = ""
        base_url = None
        system_prompt = ""
        agent_id = ""
        try:
            async with async_session() as db:
                result = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
                row = result.scalar_one_or_none()
                if row:
                    agent_id = row.agent_id or ""
                    agent_result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
                    agent_row = agent_result.scalar_one_or_none()
                    if agent_row:
                        provider = agent_row.provider or "openai"
                        model_id = agent_row.model_id or "gpt-4o"
                        base_url = agent_row.base_url
                        system_prompt = agent_row.system_prompt or ""
                        if agent_row.api_key_encrypted:
                            try:
                                from app.storage.auth import decrypt_api_key
                                api_key = decrypt_api_key(agent_row.api_key_encrypted)
                            except Exception:
                                api_key = ""
                    key_result = await db.execute(select(ApiKeyModel).where(ApiKeyModel.provider == provider).where(ApiKeyModel.is_active == True))
                    key_row = key_result.scalar_one_or_none()
                    if key_row and key_row.api_key_encrypted:
                        try:
                            from app.storage.auth import decrypt_api_key
                            api_key = decrypt_api_key(key_row.api_key_encrypted)
                        except Exception:
                            pass
                    tool_ids = list(getattr(agent_row, "tool_ids", None) or [])
        except Exception:
            tool_ids = []
        if not api_key:
            import structlog
            logger = structlog.get_logger()
            logger.warning("chat.no_api_key", session_id=session_id, provider=provider)
        session = engine.create_session(
            agent_id=agent_id,
            user_id="default-user",
            provider=provider,
            model_id=model_id,
            api_key=api_key,
            base_url=base_url,
            system_prompt=system_prompt,
            tools=tool_ids,
            session_id=session_id,
        )
        engine._sessions[session_id] = session

    async def _stream() -> Any:
        async for frame in engine.run(session, request.message):
            yield _frame_to_sse(frame)

    return StreamingResponse(_stream(), media_type="text/event-stream")


def _frame_to_sse(frame: Frame) -> str:
    payload = json.dumps(frame.to_dict(), ensure_ascii=False)
    return f"event: frame\ndata: {payload}\n\n"

"""Restricted agent execution boundary for paired external channels."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import structlog

from app.core.channel_gateway import ChannelGateway
from app.core.permission_rules import PermissionConfig

logger = structlog.get_logger()


@dataclass(frozen=True, slots=True)
class ChannelResponse:
    ok: bool
    code: str
    text: str = ""


class ChannelAgentHandler:
    """Create tool-free sessions only after exact DM pairing authorization."""

    def __init__(
        self,
        *,
        gateway: ChannelGateway,
        engine: Any,
        provider: str,
        model_id: str,
        api_key: str,
        base_url: str | None = None,
        system_prompt: str = "You are a helpful assistant.",
        owner_user_id: str = "default-user",
    ) -> None:
        self._gateway = gateway
        self._engine = engine
        self._provider = provider
        self._model_id = model_id
        self._api_key = api_key
        self._base_url = base_url
        self._system_prompt = system_prompt
        self._owner_user_id = owner_user_id
        self._sessions: dict[tuple[str, str, str], Any] = {}
        self._binding_locks: dict[tuple[str, str, str], asyncio.Lock] = {}
        self._state_lock = asyncio.Lock()

    async def handle_message(
        self,
        *,
        channel: str,
        external_user_id: str,
        conversation_id: str,
        chat_type: str,
        text: str,
    ) -> ChannelResponse:
        decision = await self._gateway.authorize(
            channel=channel,
            external_user_id=external_user_id,
            conversation_id=conversation_id,
            chat_type=chat_type,
            owner_user_id=self._owner_user_id,
        )
        if not decision.allowed:
            return ChannelResponse(False, decision.code)
        if not text.strip():
            return ChannelResponse(False, "EMPTY_MESSAGE")

        binding = (channel.strip().lower(), external_user_id.strip(), conversation_id.strip())
        lock = await self._get_binding_lock(binding)
        async with lock:
            decision = await self._gateway.authorize(
                channel=binding[0],
                external_user_id=binding[1],
                conversation_id=binding[2],
                chat_type=chat_type,
                owner_user_id=self._owner_user_id,
            )
            if not decision.allowed:
                return ChannelResponse(False, decision.code)
            try:
                session = self._sessions.get(binding)
                if session is None:
                    session = self._engine.create_session(
                        agent_id=f"channel:{binding[0]}",
                        user_id=self._owner_user_id,
                        provider=self._provider,
                        model_id=self._model_id,
                        api_key=self._api_key,
                        base_url=self._base_url,
                        system_prompt=self._system_prompt,
                        tools=[],
                    )
                    session.permission_config = PermissionConfig(denied_tools=["*"])
                    self._sessions[binding] = session

                parts: list[str] = []
                async for event in self._engine.run(session, text):
                    event_type = getattr(event.type, "value", str(event.type))
                    if event_type == "text":
                        parts.append(str(event.data.get("content", "")))
                    elif event_type == "error":
                        logger.warning("channel_agent.model_error")
                        return ChannelResponse(False, "MODEL_ERROR")
            except Exception as exc:
                logger.warning(
                    "channel_agent.model_error",
                    exception_type=type(exc).__name__,
                )
                return ChannelResponse(False, "MODEL_ERROR")

        return ChannelResponse(True, "OK", "".join(parts) or "(no response)")

    async def _get_binding_lock(self, binding: tuple[str, str, str]) -> asyncio.Lock:
        async with self._state_lock:
            return self._binding_locks.setdefault(binding, asyncio.Lock())

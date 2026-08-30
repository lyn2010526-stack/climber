from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.channel_agent_handler import ChannelResponse
from app.services.telegram_bot import TelegramAdapter, start_telegram_bot, stop_telegram_bot


class FakeChat:
    def __init__(self, chat_id: int, chat_type: str = "private") -> None:
        self.id = chat_id
        self.type = chat_type
        self.messages: list[str] = []
        self.actions: list[str] = []

    async def send_message(self, text: str) -> None:
        self.messages.append(text)

    async def send_chat_action(self, action: str) -> None:
        self.actions.append(action)


class FakeHandler:
    def __init__(self, response: ChannelResponse | None = None) -> None:
        self.calls: list[dict] = []
        self.response = response or ChannelResponse(ok=True, code="OK", text="agent reply")

    async def handle_message(self, **kwargs) -> ChannelResponse:
        self.calls.append(kwargs)
        return self.response


def update(*, chat_type: str = "private", text: str = "message"):
    chat = FakeChat(chat_id=200, chat_type=chat_type)
    return SimpleNamespace(
        effective_chat=chat,
        effective_user=SimpleNamespace(id=100),
        message=SimpleNamespace(text=text),
    )


@pytest.mark.asyncio
async def test_adapter_maps_private_telegram_identity_to_channel_binding():
    handler = FakeHandler()
    adapter = TelegramAdapter(handler)
    incoming = update()

    await adapter.handle_message(incoming, None)

    assert handler.calls == [
        {
            "channel": "telegram",
            "external_user_id": "100",
            "conversation_id": "200",
            "chat_type": "private",
            "text": "message",
        }
    ]
    assert incoming.effective_chat.actions == ["typing"]
    assert incoming.effective_chat.messages == ["agent reply"]


@pytest.mark.asyncio
async def test_adapter_rejects_non_private_chat_before_handler():
    handler = FakeHandler()
    adapter = TelegramAdapter(handler)
    incoming = update(chat_type="group")

    await adapter.handle_message(incoming, None)

    assert handler.calls == []
    assert incoming.effective_chat.messages == ["[DIRECT_MESSAGE_REQUIRED]"]


@pytest.mark.asyncio
async def test_adapter_rejects_commands_outside_private_chats():
    adapter = TelegramAdapter(FakeHandler())
    start_update = update(chat_type="group")
    capabilities_update = update(chat_type="group")

    await adapter.handle_start(start_update, None)
    await adapter.handle_capabilities(capabilities_update, None)

    assert start_update.effective_chat.messages == ["[DIRECT_MESSAGE_REQUIRED]"]
    assert capabilities_update.effective_chat.messages == ["[DIRECT_MESSAGE_REQUIRED]"]


@pytest.mark.asyncio
async def test_adapter_exposes_only_stable_error_code():
    handler = FakeHandler(
        ChannelResponse(
            ok=False,
            code="MODEL_ERROR",
            text="provider leaked secret-token",
        )
    )
    adapter = TelegramAdapter(handler)
    incoming = update()

    await adapter.handle_message(incoming, None)

    assert incoming.effective_chat.messages == ["[MODEL_ERROR]"]


@pytest.mark.asyncio
async def test_adapter_chunks_long_successful_replies():
    handler = FakeHandler(ChannelResponse(ok=True, code="OK", text="x" * 8001))
    adapter = TelegramAdapter(handler)
    incoming = update()

    await adapter.handle_message(incoming, None)

    assert [len(part) for part in incoming.effective_chat.messages] == [4000, 4000, 1]


@pytest.mark.asyncio
async def test_start_without_token_and_stop_are_backward_compatible(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    assert await start_telegram_bot() is False
    await stop_telegram_bot()

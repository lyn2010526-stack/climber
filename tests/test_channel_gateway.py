from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from app.core.channel_gateway import (
    ChannelGateway,
    PairingStatus,
)
from app.core.permission_rules import RuleDecision
from app.services.channel_agent_handler import ChannelAgentHandler


class Clock:
    def __init__(self) -> None:
        self.value = 100.0

    def __call__(self) -> float:
        return self.value


@pytest.mark.asyncio
async def test_dm_is_disabled_by_default_and_groups_are_always_rejected():
    disabled = ChannelGateway()
    enabled = ChannelGateway(dm_enabled=True)

    disabled_result = await disabled.authorize(
        channel="telegram",
        external_user_id="user-1",
        conversation_id="chat-1",
        chat_type="private",
    )
    group_result = await enabled.authorize(
        channel="telegram",
        external_user_id="user-1",
        conversation_id="chat-1",
        chat_type="group",
    )

    assert disabled_result.code == "DM_DISABLED"
    assert group_result.code == "DIRECT_MESSAGE_REQUIRED"
    assert await disabled.list_pairings(owner_user_id="default-user") == []
    assert await enabled.list_pairings(owner_user_id="default-user") == []


@pytest.mark.asyncio
async def test_pairing_requires_explicit_pending_to_paired_approval():
    gateway = ChannelGateway(dm_enabled=True)

    decision = await gateway.authorize(
        channel="telegram",
        external_user_id="user-1",
        conversation_id="chat-1",
        chat_type="private",
        owner_user_id="owner-1",
    )
    pairings = await gateway.list_pairings(owner_user_id="owner-1")

    assert decision.allowed is False
    assert decision.code == "PAIRING_PENDING"
    assert len(pairings) == 1
    assert pairings[0].status is PairingStatus.PENDING
    assert pairings[0].capability == "dm:chat"

    pairing = await gateway.approve(pairings[0].id, owner_user_id="owner-1")
    authorized = await gateway.authorize(
        channel="telegram",
        external_user_id="user-1",
        conversation_id="chat-1",
        chat_type="private",
        owner_user_id="owner-1",
    )

    assert pairing.status is PairingStatus.PAIRED
    assert authorized.allowed is True
    assert authorized.code == "PAIRED"


@pytest.mark.asyncio
async def test_pairing_is_bound_to_channel_user_and_conversation():
    gateway = ChannelGateway(dm_enabled=True)
    await gateway.authorize(
        channel="telegram",
        external_user_id="user-1",
        conversation_id="chat-1",
        chat_type="private",
    )
    pairing = (await gateway.list_pairings(owner_user_id="default-user"))[0]
    await gateway.approve(pairing.id, owner_user_id="default-user")

    changed_channel = await gateway.authorize(
        channel="signal",
        external_user_id="user-1",
        conversation_id="chat-1",
        chat_type="private",
    )
    changed_user = await gateway.authorize(
        channel="telegram",
        external_user_id="user-2",
        conversation_id="chat-1",
        chat_type="private",
    )
    changed_conversation = await gateway.authorize(
        channel="telegram",
        external_user_id="user-1",
        conversation_id="chat-2",
        chat_type="private",
    )

    assert changed_channel.allowed is False
    assert changed_user.allowed is False
    assert changed_conversation.allowed is False
    assert len(await gateway.list_pairings(owner_user_id="default-user")) == 4


@pytest.mark.asyncio
async def test_pending_pairing_expires_before_approval():
    clock = Clock()
    gateway = ChannelGateway(dm_enabled=True, pairing_ttl_seconds=30, clock=clock)
    original = await gateway.authorize(
        channel="telegram",
        external_user_id="user-1",
        conversation_id="chat-1",
        chat_type="private",
    )
    clock.value += 31
    expired = await gateway.authorize(
        channel="telegram",
        external_user_id="user-1",
        conversation_id="chat-1",
        chat_type="private",
    )

    assert expired.code == "PAIRING_PENDING"
    assert expired.pairing is not None
    assert original.pairing is not None
    assert expired.pairing.id != original.pairing.id


@pytest.mark.asyncio
async def test_approved_pairing_remains_active_until_revoked():
    clock = Clock()
    gateway = ChannelGateway(dm_enabled=True, pairing_ttl_seconds=30, clock=clock)
    await gateway.authorize(
        channel="telegram",
        external_user_id="user-1",
        conversation_id="chat-1",
        chat_type="private",
    )
    pairing = (await gateway.list_pairings(owner_user_id="default-user"))[0]
    await gateway.approve(pairing.id, owner_user_id="default-user")

    clock.value += 31
    authorized = await gateway.authorize(
        channel="telegram",
        external_user_id="user-1",
        conversation_id="chat-1",
        chat_type="private",
    )

    assert authorized.allowed is True
    assert authorized.code == "PAIRED"

    fresh = ChannelGateway(dm_enabled=True)
    await fresh.authorize(
        channel="telegram",
        external_user_id="user-1",
        conversation_id="chat-1",
        chat_type="private",
    )
    fresh_pairing = (await fresh.list_pairings(owner_user_id="default-user"))[0]
    await fresh.approve(fresh_pairing.id, owner_user_id="default-user")
    revoked = await fresh.revoke(fresh_pairing.id, owner_user_id="default-user")
    denied = await fresh.authorize(
        channel="telegram",
        external_user_id="user-1",
        conversation_id="chat-1",
        chat_type="private",
    )

    assert revoked.status is PairingStatus.REVOKED
    assert denied.code == "PAIRING_REVOKED"


@pytest.mark.asyncio
async def test_concurrent_first_messages_create_one_pending_pairing():
    gateway = ChannelGateway(dm_enabled=True)
    request = {
        "channel": "telegram",
        "external_user_id": "user-1",
        "conversation_id": "chat-1",
        "chat_type": "private",
    }

    results = await asyncio.gather(*(gateway.authorize(**request) for _ in range(10)))

    assert {result.code for result in results} == {"PAIRING_PENDING"}
    assert len(await gateway.list_pairings(owner_user_id="default-user")) == 1


@pytest.mark.asyncio
async def test_expired_pending_is_purged_before_capacity_check():
    clock = Clock()
    gateway = ChannelGateway(
        dm_enabled=True,
        pairing_ttl_seconds=30,
        max_pending_pairings=1,
        clock=clock,
    )
    await gateway.authorize(
        channel="telegram",
        external_user_id="user-1",
        conversation_id="chat-1",
        chat_type="private",
    )
    clock.value += 31

    result = await gateway.authorize(
        channel="telegram",
        external_user_id="user-2",
        conversation_id="chat-2",
        chat_type="private",
    )

    assert result.code == "PAIRING_PENDING"
    pairings = await gateway.list_pairings(owner_user_id="default-user")
    assert [pairing.external_user_id for pairing in pairings] == ["user-2"]


@pytest.mark.asyncio
async def test_pending_capacity_rejects_only_new_bindings():
    gateway = ChannelGateway(dm_enabled=True, max_pending_pairings=1)
    request = {
        "channel": "telegram",
        "external_user_id": "user-1",
        "conversation_id": "chat-1",
        "chat_type": "private",
    }
    first = await gateway.authorize(**request)

    rejected = await gateway.authorize(
        channel="telegram",
        external_user_id="user-2",
        conversation_id="chat-2",
        chat_type="private",
    )
    repeated = await gateway.authorize(**request)

    assert first.code == repeated.code == "PAIRING_PENDING"
    assert rejected.code == "PAIRING_CAPACITY_EXCEEDED"
    assert len(await gateway.list_pairings(owner_user_id="default-user")) == 1


@pytest.mark.asyncio
async def test_concurrent_distinct_bindings_respect_pending_capacity():
    gateway = ChannelGateway(dm_enabled=True, max_pending_pairings=3)

    results = await asyncio.gather(*(
        gateway.authorize(
            channel="telegram",
            external_user_id=f"user-{index}",
            conversation_id=f"chat-{index}",
            chat_type="private",
        )
        for index in range(10)
    ))

    assert sum(result.code == "PAIRING_PENDING" for result in results) == 3
    assert sum(result.code == "PAIRING_CAPACITY_EXCEEDED" for result in results) == 7
    assert len(await gateway.list_pairings(owner_user_id="default-user")) == 3


@dataclass
class FakeSession:
    session_id: str = "session-1"


class FakeEngine:
    def __init__(self) -> None:
        self.created: list[dict] = []
        self.runs: list[tuple[FakeSession, str]] = []

    def create_session(self, **kwargs):
        self.created.append(kwargs)
        return FakeSession(session_id=f"session-{len(self.created)}")

    async def run(self, session, text):
        self.runs.append((session, text))
        yield SimpleNamespace(type=SimpleNamespace(value="text"), data={"content": "reply"})
        yield SimpleNamespace(type=SimpleNamespace(value="done"), data={})


@pytest.mark.asyncio
async def test_unpaired_message_never_creates_session_or_calls_model():
    gateway = ChannelGateway(dm_enabled=True)
    engine = FakeEngine()
    handler = ChannelAgentHandler(
        gateway=gateway,
        engine=engine,
        provider="provider",
        model_id="model",
        api_key="secret",
    )

    result = await handler.handle_message(
        channel="telegram",
        external_user_id="user-1",
        conversation_id="chat-1",
        chat_type="private",
        text="private body",
    )

    assert result.code == "PAIRING_PENDING"
    assert engine.created == []
    assert engine.runs == []


@pytest.mark.asyncio
async def test_paired_external_session_has_no_tools_and_reuses_exact_binding():
    gateway = ChannelGateway(dm_enabled=True)
    engine = FakeEngine()
    handler = ChannelAgentHandler(
        gateway=gateway,
        engine=engine,
        provider="provider",
        model_id="model",
        api_key="secret",
    )
    binding = {
        "channel": "telegram",
        "external_user_id": "user-1",
        "conversation_id": "chat-1",
        "chat_type": "private",
    }
    await gateway.authorize(**binding)
    pairing = (await gateway.list_pairings(owner_user_id="default-user"))[0]
    await gateway.approve(pairing.id, owner_user_id="default-user")

    first = await handler.handle_message(**binding, text="first")
    second = await handler.handle_message(**binding, text="second")

    assert first.text == "reply"
    assert second.text == "reply"
    assert len(engine.created) == 1
    assert engine.created[0]["tools"] == []
    assert engine.runs[0][0].permission_config.evaluate("read_file", {}) is RuleDecision.DENY
    assert engine.runs[0][0].permission_config.evaluate("bash", {}) is RuleDecision.DENY
    assert len(engine.runs) == 2


@pytest.mark.asyncio
async def test_process_restart_loses_pairing_state_and_fails_closed():
    first_process = ChannelGateway(dm_enabled=True)
    await first_process.authorize(
        channel="telegram",
        external_user_id="user-1",
        conversation_id="chat-1",
        chat_type="private",
    )
    pairing = (await first_process.list_pairings(owner_user_id="default-user"))[0]
    await first_process.approve(pairing.id, owner_user_id="default-user")

    restarted_process = ChannelGateway(dm_enabled=True)
    result = await restarted_process.authorize(
        channel="telegram",
        external_user_id="user-1",
        conversation_id="chat-1",
        chat_type="private",
    )

    assert result.allowed is False
    assert result.code == "PAIRING_PENDING"

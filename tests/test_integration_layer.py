"""Tests for mixed capability integration (protocol router + event sourcing)."""

from __future__ import annotations

import pytest

from app.core.integration import EventSourcedStore, EventSourcingManager, ProtocolRouter


@pytest.mark.asyncio
async def test_protocol_router_routing():
    router = ProtocolRouter()

    async def local_handler(**kwargs):
        return f"local:{kwargs['x']}"

    async def mcp_handler(**kwargs):
        return f"mcp:{kwargs['x']}"

    router.register_handler("local", "calc", local_handler)
    router.register_handler("mcp", "calc", mcp_handler)
    router.set_default_protocol("calc", "local")

    assert router.resolve_protocol("calc") == "local"
    result = await router.call("calc", x=10)
    assert result == "local:10"


@pytest.mark.asyncio
async def test_protocol_router_unknown_raises():
    router = ProtocolRouter()
    with pytest.raises(KeyError):
        await router.call("missing", x=1)


@pytest.mark.asyncio
async def test_event_sourcing_projection_rebuild():
    mgr = EventSourcingManager()

    async def apply_convo(state, event):
        state = list(state) if state else []
        if event.get("type") == "message":
            state.append(event.get("content", ""))
        return state

    mgr.register_store(EventSourcedStore(name="conversation", apply=apply_convo, initial_state=[]))
    await mgr.emit("message", {"content": "hello"})
    await mgr.emit("message", {"content": "world"})

    snap = await mgr.snapshot()
    assert snap["conversation"] == ["hello", "world"]

    # time travel: rebuild state at an earlier point
    convo_store = mgr.get_store("conversation")
    state = await convo_store.project(upto=1)
    assert state == ["hello"]


@pytest.mark.asyncio
async def test_event_sourcing_multiple_stores_share_stream():
    mgr = EventSourcingManager()

    async def apply_counter(state, event):
        if event.get("type") == "inc":
            return (state or 0) + 1
        return state or 0

    async def apply_skills(state, event):
        state = list(state) if state else []
        if event.get("type") == "skill_created":
            state.append(event.get("name", ""))
        return state

    mgr.register_store(EventSourcedStore(name="counter", apply=apply_counter, initial_state=0))
    mgr.register_store(EventSourcedStore(name="skills", apply=apply_skills, initial_state=[]))
    await mgr.emit("inc", {})
    await mgr.emit("inc", {})
    await mgr.emit("skill_created", {"name": "send_wechat"})

    snap = await mgr.snapshot()
    assert snap["counter"] == 2
    assert snap["skills"] == ["send_wechat"]

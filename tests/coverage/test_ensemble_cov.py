"""Coverage tests for app.core.engine.ensemble.

Self-contained, deterministic, no network / external services.
"""

from __future__ import annotations

import asyncio

import pytest

from app.core.engine.ensemble import (
    AgentMessage,
    ConsensusResult,
    EnsembleCoordinator,
    EnsembleEngine,
    MessageBus,
    MessageType,
    ModelResponse,
)


def _resp(model_id: str, content: str, success: bool = True, latency: float = 1.0) -> ModelResponse:
    return ModelResponse(
        model_id=model_id,
        provider="test",
        content=content,
        success=success,
        latency_ms=latency,
    )


# --------------------------------------------------------------------------- #
# Dataclasses
# --------------------------------------------------------------------------- #
def test_consensus_result_to_dict():
    result = ConsensusResult(
        consensus_reached=True,
        consensus_content="hello world",
        consensus_model="m1",
        agreement_ratio=0.666666,
        responses=[_resp("m1", "hello world")],
        divergent_models=["m2"],
    )
    d = result.to_dict()
    assert d["consensus_reached"] is True
    assert d["consensus_model"] == "m1"
    assert d["agreement_ratio"] == 0.6667
    assert d["needs_review"] is False  # default
    assert d["divergent_models"] == ["m2"]
    assert d["response_count"] == 1


def test_model_response_defaults():
    r = ModelResponse(model_id="m", provider="p", content="c", success=True)
    assert r.latency_ms == 0.0
    assert r.tokens_used == 0
    assert r.error is None


def test_agent_message_to_dict_serializable_and_not():
    msg = AgentMessage(
        sender_id="a",
        recipient_id=None,
        msg_type=MessageType.BROADCAST,
        payload={"k": "v"},
    )
    d = msg.to_dict()
    assert d["sender_id"] == "a"
    assert d["msg_type"] == "broadcast"
    assert d["payload"] == {"k": "v"}

    obj = object()
    msg2 = AgentMessage(
        sender_id="a",
        recipient_id="b",
        msg_type=MessageType.DIRECT,
        payload=obj,
    )
    assert msg2.to_dict()["payload"] == str(obj)


def test_message_type_values():
    assert MessageType.TASK_REQUEST == "task_request"
    assert MessageType.EVENT == "event"


# --------------------------------------------------------------------------- #
# EnsembleEngine - parallel execution
# --------------------------------------------------------------------------- #
async def test_execute_parallel_success():
    engine = EnsembleEngine()

    async def runner(text: str) -> ModelResponse:
        await asyncio.sleep(0)
        return _resp("m1", f"answer {text}")

    result = await engine.execute_parallel("q", [runner, runner])
    assert isinstance(result, ConsensusResult)
    assert len(result.responses) == 2
    assert result.consensus_reached is True


async def test_execute_parallel_filters_exceptions():
    engine = EnsembleEngine()

    async def ok(text: str) -> ModelResponse:
        return _resp("ok", "same content here")

    async def boom(text: str) -> ModelResponse:
        raise RuntimeError("down")

    result = await engine.execute_parallel("q", [ok, boom])
    assert [r.model_id for r in result.responses] == ["ok"]
    assert result.consensus_reached is True


async def test_execute_parallel_all_fail():
    engine = EnsembleEngine()

    async def boom(text: str) -> ModelResponse:
        raise RuntimeError("down")

    result = await engine.execute_parallel("q", [boom, boom])
    assert result.consensus_reached is False
    assert result.needs_review is True
    assert result.responses == []


async def test_execute_parallel_respects_max_models():
    engine = EnsembleEngine(max_models=2)
    calls: list[str] = []

    async def runner(text: str) -> ModelResponse:
        calls.append(text)
        return _resp(f"m{len(calls)}", "content")

    await engine.execute_parallel("q", [runner, runner, runner, runner])
    assert len(calls) == 2


# --------------------------------------------------------------------------- #
# EnsembleEngine - consensus evaluation
# --------------------------------------------------------------------------- #
def test_evaluate_consensus_groups_and_divergence():
    engine = EnsembleEngine(consensus_threshold=0.5, similarity_threshold=0.7)
    responses = [
        _resp("m1", "the quick brown fox"),
        _resp("m2", "the quick brown fox"),
        _resp("m3", "totally different answer"),
    ]
    result = engine._evaluate_consensus(responses)
    assert result.consensus_reached is True
    assert result.consensus_model == "m1"
    assert result.agreement_ratio == pytest.approx(2 / 3)
    assert result.divergent_models == ["m3"]
    assert result.needs_review is False


def test_evaluate_consensus_not_reached():
    engine = EnsembleEngine(consensus_threshold=0.9)
    responses = [
        _resp("m1", "alpha beta gamma"),
        _resp("m2", "completely unrelated text"),
    ]
    result = engine._evaluate_consensus(responses)
    assert result.consensus_reached is False
    assert result.needs_review is True
    assert result.agreement_ratio == pytest.approx(0.5)


def test_evaluate_consensus_all_failed():
    engine = EnsembleEngine()
    responses = [_resp("m1", "x", success=False), _resp("m2", "y", success=False)]
    result = engine._evaluate_consensus(responses)
    assert result.consensus_reached is False
    assert result.needs_review is True
    assert result.responses == responses


# --------------------------------------------------------------------------- #
# EnsembleEngine - similarity + stats
# --------------------------------------------------------------------------- #
def test_is_similar_edge_cases():
    engine = EnsembleEngine(similarity_threshold=0.7)
    assert engine._is_similar("", "") is True
    assert engine._is_similar("", "x") is False
    assert engine._is_similar("x", "") is False
    assert engine._is_similar("same exact words", "same exact words") is True
    assert engine._is_similar("alpha beta", "gamma delta") is False
    # Whitespace-only strings are truthy but tokenize to an empty set.
    assert engine._is_similar("   ", "x") is False


def test_get_stats():
    engine = EnsembleEngine()
    result = ConsensusResult(
        consensus_reached=True,
        consensus_content="c",
        consensus_model="m1",
        agreement_ratio=0.5,
        responses=[
            _resp("m1", "c", latency=10.0),
            _resp("m2", "d", latency=20.0),
            _resp("m3", "e", success=False, latency=999.0),
        ],
    )
    stats = engine.get_stats(result)
    assert stats["total_responses"] == 3
    assert stats["successful_responses"] == 2
    assert stats["avg_latency_ms"] == 15.0
    assert stats["consensus_reached"] is True
    assert stats["agreement_ratio"] == 0.5


def test_get_stats_no_successes():
    engine = EnsembleEngine()
    result = ConsensusResult(
        consensus_reached=False,
        consensus_content="",
        consensus_model="",
        agreement_ratio=0.0,
        responses=[_resp("m1", "x", success=False)],
    )
    assert engine.get_stats(result)["avg_latency_ms"] == 0.0


# --------------------------------------------------------------------------- #
# MessageBus
# --------------------------------------------------------------------------- #
async def test_bus_broadcast_and_direct():
    bus = MessageBus()
    received_a: list[AgentMessage] = []
    received_b: list[AgentMessage] = []

    async def cb_a(m: AgentMessage) -> None:
        received_a.append(m)

    async def cb_b(m: AgentMessage) -> None:
        received_b.append(m)

    bus.subscribe("agent_a", cb_a)
    bus.subscribe("agent_b", cb_b)

    broadcast = AgentMessage("s", None, MessageType.BROADCAST, "hi")
    assert await bus.publish(broadcast) == 2
    assert len(received_a) == 1 and len(received_b) == 1

    direct = AgentMessage("s", "agent_a", MessageType.DIRECT, "only-a")
    assert await bus.publish(direct) == 1
    assert len(received_a) == 2
    assert len(received_b) == 1


async def test_bus_retry_succeeds_after_transient_failure():
    bus = MessageBus()
    attempts = {"n": 0}

    async def flaky(m: AgentMessage) -> None:
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise RuntimeError("transient")

    bus.subscribe("agent_a", flaky)
    notified = await bus.publish(AgentMessage("s", "agent_a", MessageType.DIRECT, "x"))
    assert notified == 1
    assert attempts["n"] == 2


async def test_bus_delivery_failure_after_retries():
    bus = MessageBus()

    async def always_fail(m: AgentMessage) -> None:
        raise RuntimeError("permanent")

    bus.subscribe("agent_a", always_fail)
    notified = await bus.publish(AgentMessage("s", "agent_a", MessageType.DIRECT, "x"))
    assert notified == 0


async def test_bus_subscribe_duplicate_is_noop():
    bus = MessageBus()
    count = {"n": 0}

    async def cb(m: AgentMessage) -> None:
        count["n"] += 1

    bus.subscribe("agent_a", cb)
    bus.subscribe("agent_a", cb)
    await bus.publish(AgentMessage("s", "agent_a", MessageType.DIRECT, "x"))
    assert count["n"] == 1
    assert bus.get_subscribers() == {"agent_a": 1}


def test_bus_unsubscribe_variants():
    bus = MessageBus()

    async def cb(m: AgentMessage) -> None:
        return None

    bus.unsubscribe("missing")  # no-op
    bus.subscribe("agent_a", cb)
    bus.unsubscribe("agent_a", cb)
    assert bus.get_subscribers()["agent_a"] == 0

    bus.subscribe("agent_a", cb)
    bus.unsubscribe("agent_a")  # remove all
    assert bus.get_subscribers() == {}


async def test_bus_history_and_filters():
    bus = MessageBus()
    await bus.publish(AgentMessage("a1", None, MessageType.BROADCAST, "m1"))
    await bus.publish(AgentMessage("a2", "a1", MessageType.DIRECT, "m2"))
    await bus.publish(AgentMessage("a1", "a2", MessageType.EVENT, "m3"))

    assert len(bus.get_history()) == 3
    by_agent = bus.get_history(agent_id="a1")
    assert {m.payload for m in by_agent} == {"m1", "m2", "m3"}
    by_type = bus.get_history(msg_type=MessageType.DIRECT)
    assert [m.payload for m in by_type] == ["m2"]
    assert [m.payload for m in bus.get_history(last_n=1)] == ["m3"]
    by_agent_type = bus.get_history(agent_id="a2", msg_type=MessageType.EVENT)
    assert [m.payload for m in by_agent_type] == ["m3"]


async def test_bus_history_cap():
    bus = MessageBus()
    bus._max_history = 2
    for i in range(3):
        await bus.publish(AgentMessage("a", None, MessageType.BROADCAST, i))
    assert [m.payload for m in bus.get_history()] == [1, 2]


# --------------------------------------------------------------------------- #
# EnsembleCoordinator
# --------------------------------------------------------------------------- #
async def test_coordinator_propose_and_vote_publishes():
    bus = MessageBus()
    engine = EnsembleEngine()
    received: list[AgentMessage] = []

    async def listener(m: AgentMessage) -> None:
        received.append(m)

    bus.subscribe("watcher", listener)
    coord = EnsembleCoordinator(bus=bus, engine=engine)

    async def runner(text: str) -> ModelResponse:
        return _resp("m1", "the answer " + text)

    result = await coord.propose_and_vote("t1", "q", [runner])
    assert result.consensus_reached is True
    assert coord.bus is bus
    assert coord.engine is engine
    assert len(received) == 1
    assert received[0].payload["task_id"] == "t1"


def test_coordinator_defaults():
    coord = EnsembleCoordinator()
    assert isinstance(coord.bus, MessageBus)
    assert isinstance(coord.engine, EnsembleEngine)

"""Tests for ensemble engine and message bus."""

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


class TestModelResponse:
    def test_creation(self) -> None:
        resp = ModelResponse(
            model_id="gpt-4o",
            provider="openai",
            content="Hello world",
            success=True,
            latency_ms=500.0,
            tokens_used=100,
        )
        assert resp.model_id == "gpt-4o"
        assert resp.success is True


class TestConsensusResult:
    def test_to_dict(self) -> None:
        result = ConsensusResult(
            consensus_reached=True,
            consensus_content="answer",
            consensus_model="gpt-4o",
            agreement_ratio=0.75,
            divergent_models=["model-b"],
        )
        d = result.to_dict()
        assert d["consensus_reached"] is True
        assert d["agreement_ratio"] == 0.75
        assert "model-b" in d["divergent_models"]


class TestEnsembleEngine:
    @pytest.mark.asyncio
    async def test_single_model(self) -> None:
        engine = EnsembleEngine()

        async def runner(task: str) -> ModelResponse:
            return ModelResponse(model_id="gpt-4o", provider="openai", content="Answer", success=True)

        result = await engine.execute_parallel("test", [runner])
        assert result.consensus_reached is True
        assert result.consensus_content == "Answer"

    @pytest.mark.asyncio
    async def test_unanimous_consensus(self) -> None:
        engine = EnsembleEngine(consensus_threshold=0.5)

        async def runner1(task: str) -> ModelResponse:
            return ModelResponse(model_id="gpt-4o", provider="openai", content="Same answer", success=True)

        async def runner2(task: str) -> ModelResponse:
            return ModelResponse(model_id="claude", provider="anthropic", content="Same answer", success=True)

        result = await engine.execute_parallel("test", [runner1, runner2])
        assert result.consensus_reached is True
        assert result.agreement_ratio == 1.0

    @pytest.mark.asyncio
    async def test_divergence(self) -> None:
        engine = EnsembleEngine(consensus_threshold=0.8)

        async def runner1(task: str) -> ModelResponse:
            return ModelResponse(model_id="gpt-4o", provider="openai", content="Option A is correct", success=True)

        async def runner2(task: str) -> ModelResponse:
            return ModelResponse(model_id="claude", provider="anthropic", content="Option B is the right choice", success=True)

        result = await engine.execute_parallel("test", [runner1, runner2])
        assert result.needs_review is True
        assert len(result.divergent_models) >= 1

    @pytest.mark.asyncio
    async def test_all_failed(self) -> None:
        engine = EnsembleEngine()

        async def bad_runner(task: str) -> ModelResponse:
            raise RuntimeError("API error")

        result = await engine.execute_parallel("test", [bad_runner])
        assert result.consensus_reached is False
        assert result.needs_review is True

    def test_is_similar_identical(self) -> None:
        engine = EnsembleEngine()
        assert engine._is_similar("hello world", "hello world") is True

    def test_is_similar_different(self) -> None:
        engine = EnsembleEngine()
        assert engine._is_similar("completely different text here", "nothing like the other one") is False

    def test_get_stats(self) -> None:
        engine = EnsembleEngine()
        result = ConsensusResult(
            consensus_reached=True,
            consensus_content="answer",
            consensus_model="gpt-4o",
            agreement_ratio=1.0,
            responses=[
                ModelResponse(model_id="gpt-4o", provider="openai", content="answer", success=True, latency_ms=100.0),
            ],
        )
        stats = engine.get_stats(result)
        assert stats["total_responses"] == 1
        assert stats["avg_latency_ms"] == 100.0


class TestMessageBus:
    @pytest.mark.asyncio
    async def test_publish_broadcast(self) -> None:
        bus = MessageBus()
        received: list[AgentMessage] = []

        async def handler(msg: AgentMessage) -> None:
            received.append(msg)

        bus.subscribe("agent-1", handler)
        await bus.publish(AgentMessage(
            sender_id="sender",
            recipient_id=None,
            msg_type=MessageType.BROADCAST,
            payload="hello",
        ))
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_publish_direct(self) -> None:
        bus = MessageBus()
        received: list[AgentMessage] = []

        async def handler(msg: AgentMessage) -> None:
            received.append(msg)

        bus.subscribe("agent-1", handler)
        await bus.publish(AgentMessage(
            sender_id="sender",
            recipient_id="agent-1",
            msg_type=MessageType.DIRECT,
            payload="private",
        ))
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_direct_message_filtered(self) -> None:
        bus = MessageBus()
        received: list[AgentMessage] = []

        async def handler(msg: AgentMessage) -> None:
            received.append(msg)

        bus.subscribe("agent-1", handler)
        await bus.publish(AgentMessage(
            sender_id="sender",
            recipient_id="agent-2",  # Different recipient
            msg_type=MessageType.DIRECT,
            payload="private",
        ))
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_unsubscribe(self) -> None:
        bus = MessageBus()
        count = 0

        async def handler(msg: AgentMessage) -> None:
            nonlocal count
            count += 1

        bus.subscribe("agent-1", handler)
        bus.unsubscribe("agent-1", handler)
        await bus.publish(AgentMessage(
            sender_id="sender",
            recipient_id=None,
            msg_type=MessageType.BROADCAST,
            payload="hello",
        ))
        assert count == 0

    @pytest.mark.asyncio
    async def test_history(self) -> None:
        bus = MessageBus()
        await bus.publish(AgentMessage(
            sender_id="sender",
            recipient_id=None,
            msg_type=MessageType.BROADCAST,
            payload="msg1",
        ))
        await bus.publish(AgentMessage(
            sender_id="sender",
            recipient_id=None,
            msg_type=MessageType.TASK_REQUEST,
            payload="msg2",
        ))
        all_msgs = bus.get_history()
        assert len(all_msgs) == 2
        task_msgs = bus.get_history(msg_type=MessageType.TASK_REQUEST)
        assert len(task_msgs) == 1

    def test_get_subscribers(self) -> None:
        bus = MessageBus()

        async def handler(msg: AgentMessage) -> None:
            pass

        bus.subscribe("agent-1", handler)
        bus.subscribe("agent-1", handler)
        bus.subscribe("agent-2", handler)
        stats = bus.get_subscribers()
        assert stats["agent-1"] == 2
        assert stats["agent-2"] == 1


class TestEnsembleCoordinator:
    @pytest.mark.asyncio
    async def test_propose_and_vote(self) -> None:
        coordinator = EnsembleCoordinator()

        async def runner(task: str) -> ModelResponse:
            return ModelResponse(model_id="gpt-4o", provider="openai", content="Consensus answer", success=True)

        result = await coordinator.propose_and_vote("task-1", "test", [runner])
        assert result.consensus_reached is True
        # Message should have been published
        history = coordinator.bus.get_history()
        assert len(history) >= 1

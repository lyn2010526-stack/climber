"""Ensemble execution engine and message bus.

Reference: OpenSquilla Ensemble (multi-model parallel execution with consensus),
AutoGen AgentRuntime Protocol (publish/subscribe messaging).

Features:
- Multi-model parallel execution for same task
- Voting-based consensus with configurable threshold
- Divergence detection and needs_review flagging
- Publish/subscribe message bus for inter-agent communication
- Async event-driven architecture
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class ModelResponse:
    """Response from a single model in ensemble."""
    model_id: str
    provider: str
    content: str
    success: bool
    latency_ms: float = 0.0
    tokens_used: int = 0
    error: str | None = None


@dataclass
class ConsensusResult:
    """Result of ensemble consensus evaluation."""
    consensus_reached: bool
    consensus_content: str
    consensus_model: str
    agreement_ratio: float
    responses: list[ModelResponse] = field(default_factory=list)
    divergent_models: list[str] = field(default_factory=list)
    needs_review: bool = False
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])

    def to_dict(self) -> dict[str, Any]:
        return {
            "consensus_reached": self.consensus_reached,
            "consensus_model": self.consensus_model,
            "agreement_ratio": round(self.agreement_ratio, 4),
            "needs_review": self.needs_review,
            "divergent_models": self.divergent_models,
            "response_count": len(self.responses),
        }


class EnsembleEngine:
    """Multi-model parallel execution with consensus voting.

    Reference: OpenSquilla Ensemble — run same task on N models,
    vote on result, flag divergence for review.
    """

    def __init__(
        self,
        *,
        consensus_threshold: float = 0.5,
        similarity_threshold: float = 0.7,
        max_models: int = 4,
        default_timeout: float = 60.0,
    ) -> None:
        self._consensus_threshold = consensus_threshold
        self._similarity_threshold = similarity_threshold
        self._max_models = max_models
        self._default_timeout = default_timeout

    async def execute_parallel(
        self,
        task: str,
        runners: list[Callable[[str], Awaitable[ModelResponse]]],
    ) -> ConsensusResult:
        """Execute task on multiple models in parallel and compute consensus.

        Args:
            task: Task description
            runners: List of async callables that each invoke a model

        Returns:
            ConsensusResult with consensus decision
        """
        # Execute all runners in parallel
        tasks = [r(task) for r in runners[:self._max_models]]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        valid_responses: list[ModelResponse] = []
        for r in responses:
            if isinstance(r, Exception):
                continue
            valid_responses.append(r)

        if not valid_responses:
            return ConsensusResult(
                consensus_reached=False,
                consensus_content="",
                consensus_model="",
                agreement_ratio=0.0,
                needs_review=True,
            )

        return self._evaluate_consensus(valid_responses)

    def _evaluate_consensus(self, responses: list[ModelResponse]) -> ConsensusResult:
        """Evaluate consensus among model responses."""
        # Group by content similarity
        groups: list[list[ModelResponse]] = []

        for resp in responses:
            if not resp.success:
                continue
            placed = False
            for group in groups:
                if self._is_similar(resp.content, group[0].content):
                    group.append(resp)
                    placed = True
                    break
            if not placed:
                groups.append([resp])

        if not groups:
            return ConsensusResult(
                consensus_reached=False,
                consensus_content="",
                consensus_model="",
                agreement_ratio=0.0,
                responses=responses,
                needs_review=True,
            )

        # Find largest group
        largest = max(groups, key=len)
        agreement_ratio = len(largest) / len(responses)

        # Determine divergent models
        consensus_models = {r.model_id for r in largest}
        divergent = [r.model_id for r in responses if r.model_id not in consensus_models]

        consensus_reached = agreement_ratio >= self._consensus_threshold

        return ConsensusResult(
            consensus_reached=consensus_reached,
            consensus_content=largest[0].content,
            consensus_model=largest[0].model_id,
            agreement_ratio=agreement_ratio,
            responses=responses,
            divergent_models=divergent,
            needs_review=not consensus_reached,
        )

    def _is_similar(self, a: str, b: str) -> bool:
        """Check if two responses are semantically similar (simplified).

        Uses Jaccard similarity on word tokens as lightweight heuristic.
        Production systems should use embedding-based similarity.
        """
        if not a or not b:
            return a == b

        # Normalize
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())

        if not words_a or not words_b:
            return False

        intersection = words_a & words_b
        union = words_a | words_b
        jaccard = len(intersection) / len(union) if union else 0.0

        return jaccard >= self._similarity_threshold

    def get_stats(self, result: ConsensusResult) -> dict[str, Any]:
        """Get statistics for a consensus result."""
        latencies = [r.latency_ms for r in result.responses if r.success]
        return {
            "total_responses": len(result.responses),
            "successful_responses": sum(1 for r in result.responses if r.success),
            "avg_latency_ms": round(sum(latencies) / max(len(latencies), 1), 2),
            "consensus_reached": result.consensus_reached,
            "agreement_ratio": round(result.agreement_ratio, 4),
        }


class MessageType(StrEnum):
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    BROADCAST = "broadcast"
    DIRECT = "direct"
    SYSTEM = "system"
    EVENT = "event"


@dataclass
class AgentMessage:
    """Message passed between agents on the bus."""
    sender_id: str
    recipient_id: str | None  # None = broadcast
    msg_type: MessageType
    payload: Any
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    timestamp: float = field(default_factory=time.monotonic)
    reply_to: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "msg_id": self.msg_id,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "msg_type": self.msg_type.value,
            "payload": self.payload if isinstance(self.payload, (str, int, float, bool, dict, list, type(None))) else str(self.payload),
            "timestamp": self.timestamp,
            "reply_to": self.reply_to,
        }


class MessageBus:
    """Publish/subscribe message bus for inter-agent communication.

    Reference: AutoGen AgentRuntime Protocol — agents communicate via
    publish/subscribe on topic-based channels.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[AgentMessage], Awaitable[None]]]] = {}
        self._history: list[AgentMessage] = []
        self._max_history = 500

    async def publish(self, message: AgentMessage) -> int:
        """Publish a message to all relevant subscribers.

        Returns:
            Number of subscribers notified
        """
        self._history.append(message)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history // 2:]

        notified = 0

        # Direct message: only notify specific recipient
        if message.recipient_id:
            subscribers = self._subscribers.get(message.recipient_id, [])
        else:
            # Broadcast: notify all subscribers
            subscribers = []
            for subs in self._subscribers.values():
                subscribers.extend(subs)

        for callback in subscribers:
            try:
                await callback(message)
                notified += 1
            except Exception as e:
                logger.warning("message_bus.delivery_failed", error=str(e), msg_id=message.msg_id)

        return notified

    def subscribe(self, agent_id: str, callback: Callable[[AgentMessage], Awaitable[None]]) -> None:
        """Subscribe an agent to receive messages."""
        if agent_id not in self._subscribers:
            self._subscribers[agent_id] = []
        self._subscribers[agent_id].append(callback)

    def unsubscribe(self, agent_id: str, callback: Callable[[AgentMessage], Awaitable[None]] | None = None) -> None:
        """Unsubscribe an agent. If callback is None, remove all subscriptions."""
        if agent_id not in self._subscribers:
            return
        if callback is None:
            del self._subscribers[agent_id]
        else:
            self._subscribers[agent_id] = [cb for cb in self._subscribers[agent_id] if cb != callback]

    def get_history(
        self,
        *,
        agent_id: str | None = None,
        msg_type: MessageType | None = None,
        last_n: int = 50,
    ) -> list[AgentMessage]:
        """Get message history with optional filtering."""
        filtered = self._history

        if agent_id:
            filtered = [m for m in filtered if m.recipient_id == agent_id or m.sender_id == agent_id]

        if msg_type:
            filtered = [m for m in filtered if m.msg_type == msg_type]

        return filtered[-last_n:]

    def get_subscribers(self) -> dict[str, int]:
        """Get subscriber counts per agent."""
        return {agent_id: len(callbacks) for agent_id, callbacks in self._subscribers.items()}


class EnsembleCoordinator:
    """Coordinates ensemble execution with message bus integration.

    Combines EnsembleEngine for voting and MessageBus for result distribution.
    """

    def __init__(
        self,
        bus: MessageBus | None = None,
        engine: EnsembleEngine | None = None,
    ) -> None:
        self._bus = bus or MessageBus()
        self._engine = engine or EnsembleEngine()

    async def propose_and_vote(
        self,
        task_id: str,
        task: str,
        runners: list[Callable[[str], Awaitable[ModelResponse]]],
    ) -> ConsensusResult:
        """Run ensemble and publish result to bus."""
        result = await self._engine.execute_parallel(task, runners)

        # Publish result
        await self._bus.publish(AgentMessage(
            sender_id="ensemble_coordinator",
            recipient_id=None,  # Broadcast
            msg_type=MessageType.TASK_RESPONSE,
            payload={
                "task_id": task_id,
                "result": result.to_dict(),
                "consensus_content": result.consensus_content[:500],
            },
            metadata={"consensus_reached": result.consensus_reached},
        ))

        return result

    @property
    def bus(self) -> MessageBus:
        return self._bus

    @property
    def engine(self) -> EnsembleEngine:
        return self._engine

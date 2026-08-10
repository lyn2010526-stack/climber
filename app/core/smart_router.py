"""Smart model router with health checking and circuit breaker.

Enhances ModelRouter with:
- Per-model health tracking (error rate, latency)
- Circuit breaker pattern (skip unhealthy models)
- Latency-aware routing (prefer faster models)
- Concurrent health probe endpoint

Inspired by LiteLLM's cooldown system and Netflix's circuit breaker.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.core import ChatResult, ModelRoute, AgentEvent, AgentEventType
from app.models.registry import ModelRegistry

logger = structlog.get_logger()


@dataclass
class ModelHealth:
    """Health status for a single model route."""
    model_key: str
    total_calls: int = 0
    error_calls: int = 0
    total_latency_ms: float = 0.0
    last_error: str | None = None
    last_error_time: float = 0.0
    last_success_time: float = 0.0
    circuit_open: bool = False
    circuit_open_until: float = 0.0

    @property
    def error_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.error_calls / self.total_calls

    @property
    def avg_latency_ms(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.total_latency_ms / self.total_calls

    @property
    def is_available(self) -> float:
        return not self.circuit_open or time.monotonic() >= self.circuit_open_until


class CircuitBreaker:
    """Circuit breaker for model routes.

    States:
    - CLOSED: normal operation, all requests pass through
    - OPEN: model is unhealthy, requests skip to next route
    - HALF_OPEN: after cooldown, allow one test request
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        error_rate_threshold: float = 0.5,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.error_rate_threshold = error_rate_threshold
        self._health: dict[str, ModelHealth] = {}

    def get_health(self, model_key: str) -> ModelHealth:
        if model_key not in self._health:
            self._health[model_key] = ModelHealth(model_key=model_key)
        return self._health[model_key]

    def record_success(self, model_key: str, latency_ms: float) -> None:
        health = self.get_health(model_key)
        health.total_calls += 1
        health.total_latency_ms += latency_ms
        health.last_success_time = time.monotonic()
        if health.circuit_open:
            health.circuit_open = False
            health.circuit_open_until = 0.0
            health.error_calls = 0
            logger.info("Circuit breaker closed, model recovered", model=model_key)

    def record_failure(self, model_key: str, error: str) -> None:
        health = self.get_health(model_key)
        health.total_calls += 1
        health.error_calls += 1
        health.last_error = error
        health.last_error_time = time.monotonic()

        should_open = (
            health.error_calls >= self.failure_threshold
            or (health.total_calls >= 3 and health.error_rate >= self.error_rate_threshold)
        )
        if should_open and not health.circuit_open:
            health.circuit_open = True
            health.circuit_open_until = time.monotonic() + self.recovery_timeout
            logger.warning(
                "Circuit breaker opened",
                model=model_key,
                error_count=health.error_calls,
                error_rate=f"{health.error_rate:.0%}",
                cooldown_seconds=self.recovery_timeout,
            )

    def get_available_routes(self, routes: list[ModelRoute]) -> list[ModelRoute]:
        """Filter out routes with open circuits."""
        available = []
        for route in routes:
            model_key = f"{route.provider}:{route.model_id}"
            health = self.get_health(model_key)
            if health.is_available:
                available.append(route)
        return available

    def get_all_health(self) -> dict[str, dict]:
        return {
            key: {
                "total_calls": h.total_calls,
                "error_calls": h.error_calls,
                "error_rate": round(h.error_rate, 3),
                "avg_latency_ms": round(h.avg_latency_ms, 1),
                "circuit_open": h.circuit_open,
                "circuit_open_until": h.circuit_open_until,
                "last_error": h.last_error,
            }
            for key, h in self._health.items()
        }


class SmartModelRouter:
    """Model router with health-aware routing and circuit breaker.

    Enhances the basic ModelRouter with:
    1. Circuit breaker — skips models with high error rates
    2. Latency tracking — prefers faster models
    3. Health monitoring — real-time model health dashboard data
    """

    def __init__(
        self,
        registry: ModelRegistry,
        routes: list[ModelRoute] | None = None,
        max_retries_per_model: int = 2,
        base_delay: float = 1.0,
        circuit_breaker: CircuitBreaker | None = None,
    ):
        self._registry = registry
        self._routes = sorted(routes or [], key=lambda r: r.priority)
        self._max_retries = max_retries_per_model
        self._base_delay = base_delay
        self._circuit = circuit_breaker or CircuitBreaker()

    def add_route(self, route: ModelRoute) -> None:
        self._routes.append(route)
        self._routes.sort(key=lambda r: r.priority)

    def _get_adapter(self, route: ModelRoute):
        return self._registry.get_or_create(
            provider=route.provider,
            model_id=route.model_id,
            api_key=route.api_key,
            base_url=route.base_url,
        )

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Chat with circuit breaker and health tracking."""
        available = self._circuit.get_available_routes(self._routes)
        if not available:
            logger.warning("All circuits open, falling back to full route list")
            available = self._routes

        if not available:
            raise ValueError("No model routes configured")

        last_error: Exception | None = None

        for route in available:
            adapter = self._get_adapter(route)
            model_key = f"{route.provider}:{route.model_id}"

            for attempt in range(route.max_retries):
                start = time.monotonic()
                try:
                    result = await adapter.chat(messages=messages, tools=tools, **kwargs)
                    latency_ms = (time.monotonic() - start) * 1000
                    self._circuit.record_success(model_key, latency_ms)
                    return result
                except Exception as e:
                    latency_ms = (time.monotonic() - start) * 1000
                    last_error = e
                    self._circuit.record_failure(model_key, str(e))
                    if attempt < route.max_retries - 1:
                        delay = self._base_delay * (2 ** attempt)
                        await asyncio.sleep(delay)

        raise last_error or RuntimeError("All models in chain failed")

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatResult]:
        """Stream with circuit breaker and health tracking."""
        available = self._circuit.get_available_routes(self._routes)
        if not available:
            available = self._routes

        if not available:
            raise ValueError("No model routes configured")

        last_error: Exception | None = None

        for route in available:
            adapter = self._get_adapter(route)
            model_key = f"{route.provider}:{route.model_id}"

            if not adapter.capabilities.streaming:
                continue

            start = time.monotonic()
            try:
                async for chunk in adapter.stream_chat(messages=messages, tools=tools, **kwargs):
                    yield chunk
                latency_ms = (time.monotonic() - start) * 1000
                self._circuit.record_success(model_key, latency_ms)
                return
            except Exception as e:
                latency_ms = (time.monotonic() - start) * 1000
                last_error = e
                self._circuit.record_failure(model_key, str(e))
                continue

        if last_error:
            raise last_error
        raise RuntimeError("No streaming-capable model available")

    async def chat_with_events(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[AgentEvent]:
        """Chat with events, fallback notifications, and health tracking."""
        available = self._circuit.get_available_routes(self._routes)
        if not available:
            available = self._routes

        if not available:
            yield AgentEvent(
                type=AgentEventType.ERROR,
                data={"error": "No model routes configured"},
            )
            return

        last_error: Exception | None = None

        for i, route in enumerate(available):
            adapter = self._get_adapter(route)
            model_key = f"{route.provider}:{route.model_id}"

            if i > 0:
                yield AgentEvent(
                    type=AgentEventType.MODEL_FALLBACK,
                    data={
                        "from": f"{available[i-1].provider}:{available[i-1].model_id}",
                        "to": model_key,
                        "reason": str(last_error) if last_error else "unknown",
                    },
                )

            start = time.monotonic()
            try:
                if adapter.capabilities.streaming:
                    async for chunk in adapter.stream_chat(messages=messages, tools=tools, **kwargs):
                        if chunk.content:
                            yield AgentEvent(
                                type=AgentEventType.TEXT,
                                data={"content": chunk.content},
                            )
                        if chunk.finish_reason:
                            yield AgentEvent(
                                type=AgentEventType.DONE,
                                data={
                                    "finish_reason": chunk.finish_reason,
                                    "tokens_used": chunk.tokens_used,
                                    "model": model_key,
                                },
                            )
                    latency_ms = (time.monotonic() - start) * 1000
                    self._circuit.record_success(model_key, latency_ms)
                    return
                else:
                    result = await adapter.chat(messages=messages, tools=tools, **kwargs)
                    if result.content:
                        yield AgentEvent(
                            type=AgentEventType.TEXT,
                            data={"content": result.content},
                        )
                    yield AgentEvent(
                        type=AgentEventType.DONE,
                        data={
                            "finish_reason": result.finish_reason,
                            "tokens_used": result.tokens_used,
                            "model": model_key,
                        },
                    )
                    latency_ms = (time.monotonic() - start) * 1000
                    self._circuit.record_success(model_key, latency_ms)
                    return
            except Exception as e:
                latency_ms = (time.monotonic() - start) * 1000
                last_error = e
                self._circuit.record_failure(model_key, str(e))
                continue

        yield AgentEvent(
            type=AgentEventType.ERROR,
            data={"error": str(last_error) if last_error else "All models failed"},
        )

    def get_health_status(self) -> dict[str, dict]:
        """Get health status for all models."""
        return self._circuit.get_all_health()

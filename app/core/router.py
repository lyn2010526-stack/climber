"""Model router with fallback chains — Dify-style intelligent routing.

Supports:
- Priority-based model selection
- Automatic failover on error
- Cost-aware routing (cheaper model on failure)
- Retry with exponential backoff
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import structlog

from app.core import AgentEvent, AgentEventType, ChatResult, FallbackStrategy, ModelRoute
from app.models import ModelAdapter
from app.models.registry import ModelRegistry

logger = structlog.get_logger()


class ModelRouter:
    """Routes chat requests through a chain of models with automatic fallback.

    When the primary model fails (rate limit, timeout, error), automatically
    tries the next model in the chain. Inspired by Dify's model fallback
    and LangGraph's retry policy.
    """

    def __init__(
        self,
        registry: ModelRegistry,
        routes: list[ModelRoute] | None = None,
        strategy: FallbackStrategy = FallbackStrategy.NEXT_MODEL,
        max_retries_per_model: int = 2,
        base_delay: float = 1.0,
    ):
        self._registry = registry
        self._routes = sorted(routes or [], key=lambda r: r.priority)
        self._strategy = strategy
        self._max_retries = max_retries_per_model
        self._base_delay = base_delay

    def add_route(self, route: ModelRoute) -> None:
        """Add a model to the routing chain."""
        self._routes.append(route)
        self._routes.sort(key=lambda r: r.priority)

    def _get_adapter(self, route: ModelRoute) -> ModelAdapter:
        """Get or create adapter for a route."""
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
        """Send chat through the model chain with automatic fallback."""
        if not self._routes:
            raise ValueError("No model routes configured")

        last_error: Exception | None = None
        attempted_models: list[str] = []

        for route in self._routes:
            adapter = self._get_adapter(route)
            model_key = f"{route.provider}:{route.model_id}"
            attempted_models.append(model_key)

            for attempt in range(route.max_retries):
                try:
                    result = await adapter.chat(messages=messages, tools=tools, **kwargs)
                    if attempt > 0 or len(attempted_models) > 1:
                        logger.info(
                            "Model succeeded after fallback",
                            model=model_key,
                            attempt=attempt + 1,
                            attempted=attempted_models,
                        )
                    return result
                except Exception as e:
                    last_error = e
                    if attempt < route.max_retries - 1:
                        delay = self._base_delay * (2 ** attempt)
                        logger.warning(
                            "Model attempt failed, retrying",
                            model=model_key,
                            attempt=attempt + 1,
                            delay=delay,
                            error=str(e),
                        )
                        await asyncio.sleep(delay)

            logger.warning("Model exhausted retries", model=model_key)

        raise last_error or RuntimeError("All models in chain failed")

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatResult]:
        """Stream chat through the model chain with fallback on error."""
        if not self._routes:
            raise ValueError("No model routes configured")

        last_error: Exception | None = None

        for route in self._routes:
            adapter = self._get_adapter(route)
            model_key = f"{route.provider}:{route.model_id}"

            if not adapter.capabilities.streaming:
                continue

            try:
                async for chunk in adapter.stream_chat(messages=messages, tools=tools, **kwargs):
                    yield chunk
                return
            except Exception as e:
                last_error = e
                logger.warning("Streaming model failed, trying next", model=model_key, error=str(e))
                continue

        if last_error:
            raise last_error
        raise RuntimeError("No streaming-capable model available in chain")

    async def chat_with_events(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[AgentEvent]:
        """Chat with streaming events including fallback notifications."""
        if not self._routes:
            raise ValueError("No model routes configured")

        last_error: Exception | None = None

        for i, route in enumerate(self._routes):
            adapter = self._get_adapter(route)
            model_key = f"{route.provider}:{route.model_id}"

            if i > 0:
                yield AgentEvent(
                    type=AgentEventType.MODEL_FALLBACK,
                    data={
                        "from": f"{self._routes[i-1].provider}:{self._routes[i-1].model_id}",
                        "to": model_key,
                        "reason": str(last_error) if last_error else "unknown",
                    },
                )

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
                    return
            except Exception as e:
                last_error = e
                logger.warning("Model failed in event chain", model=model_key, error=str(e))
                continue

        yield AgentEvent(
            type=AgentEventType.ERROR,
            data={"error": str(last_error) if last_error else "All models failed"},
        )

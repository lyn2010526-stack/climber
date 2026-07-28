"""LiteLLM-style gateway enhancement with API key rotation.

"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import structlog

from app.core import ChatResult
from app.core.key_rotator import ApiKeyRotator, ApiKeyRotatorError, KeyRotationConfig, RotationStrategy
from app.models import ModelAdapter, ModelCapability
from app.models.registry import ModelRegistry, PROVIDERS

logger = structlog.get_logger()


@dataclass
class LiteLLMConfig:
    router: str = "least-busy"  # least-busy / usage-based / latency-based
    fallbacks: list[str] = field(default_factory=list)
    retry_count: int = 3
    timeout: float = 60.0
    budget: dict[str, Any] | None = None


class LiteLLMGateway:
    """Enhanced model gateway with retry/fallback/routing and key rotation.

    """

    def __init__(
        self,
        registry: ModelRegistry,
        config: LiteLLMConfig | None = None,
        key_rotator: ApiKeyRotator | None = None,
    ):
        self.registry = registry
        self.config = config or LiteLLMConfig()
        self.key_rotator = key_rotator or ApiKeyRotator()
        self._usage: dict[str, dict[str, int]] = {}

    def select_model(self, preferred: str) -> str:
        """Select model based on routing strategy."""
        if self.config.router == "least-busy":
            return self._select_least_busy(preferred)
        return preferred

    def _select_least_busy(self, preferred: str) -> str:
        """Select the least busy model."""
        candidates = [preferred] + self.config.fallbacks
        best = preferred
        min_usage = float("inf")
        for model in candidates:
            usage = self._usage.get(model, {}).get("requests", 0)
            if usage < min_usage:
                min_usage = usage
                best = model
        return best

    def record_usage(self, model: str, tokens: int) -> None:
        if model not in self._usage:
            self._usage[model] = {"requests": 0, "tokens": 0}
        self._usage[model]["requests"] += 1
        self._usage[model]["tokens"] += tokens

    def get_fallback_chain(self, preferred: str) -> list[str]:
        return [preferred] + [f for f in self.config.fallbacks if f != preferred]

    def _is_key_rotation_error(self, error: str) -> bool:
        """Check if an error should trigger key rotation."""
        error_lower = error.lower()
        return (
            "401" in error
            or "403" in error
            or "429" in error
            or "unauthorized" in error_lower
            or "forbidden" in error_lower
            or "rate limit" in error_lower
        )

    async def chat_with_key_rotation(
        self,
        provider: str,
        model_id: str,
        messages: list[dict[str, Any]],
        api_keys: list[str],
        tools: list[dict[str, Any]] | None = None,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Chat with automatic API key rotation on auth/rate-limit errors.


        Flow:
        1. Register keys with rotator (if not already registered)
        2. For each attempt:
           a. Acquire next healthy key from rotator
           b. Create adapter directly with that key (bypass registry cache)
           c. Make request
           d. Report success/failure to rotator
           e. On 401/403/429, release key and retry with next key
        """
        if not api_keys:
            raise ValueError(f"No API keys provided for {provider}")

        self.key_rotator.register_keys(provider, api_keys)

        last_error: Exception | None = None
        attempted_keys: list[str] = []

        for attempt in range(self.config.retry_count):
            key_metrics = await self.key_rotator.acquire_key(provider)
            if key_metrics is None:
                raise ApiKeyRotatorError(
                    f"No healthy API keys available for provider: {provider}"
                )

            api_key = key_metrics.api_key
            key_prefix = key_metrics.key_prefix
            attempted_keys.append(key_prefix)

            try:
                adapter = self._create_adapter(provider, model_id, api_key, base_url)

                result = await adapter.chat(messages=messages, tools=tools, **kwargs)
                self.key_rotator.release_key(provider, key_prefix)
                self.key_rotator.report_success(provider, key_prefix, result.tokens_used)
                self.record_usage(f"{provider}:{model_id}", result.tokens_used)
                return result

            except Exception as exc:
                error_str = str(exc)
                self.key_rotator.release_key(provider, key_prefix)

                if self._is_key_rotation_error(error_str):
                    self.key_rotator.report_failure(provider, key_prefix, error_str)
                    if attempt < self.config.retry_count - 1:
                        self.key_rotator.report_retry(provider, key_prefix, error_str)
                        logger.warning(
                            "Key rotation: retrying with next key",
                            provider=provider,
                            model=model_id,
                            attempt=attempt + 1,
                            key_prefix=key_prefix,
                            error=error_str[:100],
                        )
                        continue

                self.key_rotator.report_failure(provider, key_prefix, error_str)
                last_error = exc
                break

        raise last_error or ApiKeyRotatorError(
            f"All keys exhausted for {provider}:{model_id}, attempted: {attempted_keys}"
        )

    async def stream_with_key_rotation(
        self,
        provider: str,
        model_id: str,
        messages: list[dict[str, Any]],
        api_keys: list[str],
        tools: list[dict[str, Any]] | None = None,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatResult]:
        """Stream chat with automatic API key rotation on auth/rate-limit errors."""
        if not api_keys:
            raise ValueError(f"No API keys provided for {provider}")

        self.key_rotator.register_keys(provider, api_keys)

        last_error: Exception | None = None
        attempted_keys: list[str] = []

        for attempt in range(self.config.retry_count):
            key_metrics = await self.key_rotator.acquire_key(provider)
            if key_metrics is None:
                raise ApiKeyRotatorError(
                    f"No healthy API keys available for provider: {provider}"
                )

            api_key = key_metrics.api_key
            key_prefix = key_metrics.key_prefix
            attempted_keys.append(key_prefix)

            try:
                adapter = self._create_adapter(provider, model_id, api_key, base_url)

                if not adapter.capabilities.streaming:
                    self.key_rotator.release_key(provider, key_prefix)
                    result = await adapter.chat(messages=messages, tools=tools, **kwargs)
                    self.key_rotator.report_success(provider, key_prefix, result.tokens_used)
                    yield ChatResult(
                        content=result.content,
                        tool_calls=result.tool_calls,
                        finish_reason=result.finish_reason,
                        tokens_used=result.tokens_used,
                    )
                    return

                tokens_used = 0
                async for chunk in adapter.stream_chat(messages=messages, tools=tools, **kwargs):
                    tokens_used = max(tokens_used, chunk.tokens_used or 0)
                    yield chunk

                self.key_rotator.release_key(provider, key_prefix)
                self.key_rotator.report_success(provider, key_prefix, tokens_used)
                self.record_usage(f"{provider}:{model_id}", tokens_used)
                return

            except Exception as exc:
                error_str = str(exc)
                self.key_rotator.release_key(provider, key_prefix)

                if self._is_key_rotation_error(error_str):
                    self.key_rotator.report_failure(provider, key_prefix, error_str)
                    if attempt < self.config.retry_count - 1:
                        self.key_rotator.report_retry(provider, key_prefix, error_str)
                        logger.warning(
                            "Key rotation: retrying stream with next key",
                            provider=provider,
                            model=model_id,
                            attempt=attempt + 1,
                            key_prefix=key_prefix,
                            error=error_str[:100],
                        )
                        continue

                self.key_rotator.report_failure(provider, key_prefix, error_str)
                last_error = exc
                break

        raise last_error or ApiKeyRotatorError(
            f"All keys exhausted for {provider}:{model_id} streaming, attempted: {attempted_keys}"
        )

    def _create_adapter(
        self,
        provider: str,
        model_id: str,
        api_key: str,
        base_url: str | None = None,
    ) -> ModelAdapter:
        """Create a fresh adapter instance for key rotation.

        Bypasses registry cache so each key gets its own adapter instance.
        Adapters share underlying HTTP connection pools via class-level clients.
        """
        adapter_cls = PROVIDERS.get(provider)
        if not adapter_cls:
            raise ValueError(
                f"Unknown provider: {provider}. Supported: {list(PROVIDERS.keys())}"
            )
        kwargs: dict[str, Any] = {"model_id": model_id, "api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        return adapter_cls(**kwargs)

    def get_key_stats(self, provider: str, key_prefix: str | None = None) -> dict[str, Any]:
        """Get key rotation stats for a provider."""
        return self.key_rotator.get_key_stats(provider, key_prefix)

    def get_all_key_stats(self) -> dict[str, Any]:
        """Get key rotation stats for all providers."""
        return self.key_rotator.get_all_stats()


# Monkey-patch ModelRegistry if available
def enhance_model_registry(registry: Any) -> LiteLLMGateway:
    gateway = LiteLLMGateway(registry)
    original_get = registry.get_or_create if hasattr(registry, "get_or_create") else None

    if original_get:
        def enhanced_get(provider: str, model_id: str, **kwargs):
            selected = gateway.select_model(f"{provider}/{model_id}")
            p, m = selected.split("/", 1) if "/" in selected else (provider, model_id)
            return original_get(p, m, **kwargs)

        registry.get_or_create = enhanced_get
    return gateway

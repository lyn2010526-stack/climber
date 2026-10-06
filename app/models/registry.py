"""Model registry - manages and routes to different model adapters."""

from __future__ import annotations

import os
from typing import Any

import structlog

from app.models import ModelAdapter, ModelCapability
from app.models.anthropic_adapter import AnthropicAdapter
from app.models.google_adapter import GoogleGeminiAdapter
from app.models.ollama_adapter import OllamaAdapter
from app.models.openai_adapter import OpenAIAdapter
from app.models.stepfun_adapter import StepFunAdapter

logger = structlog.get_logger()

# Supported provider constructors
PROVIDERS: dict[str, type[ModelAdapter]] = {
    "openai": OpenAIAdapter,
    "anthropic": AnthropicAdapter,
    "google": GoogleGeminiAdapter,
    "ollama": OllamaAdapter,
    "stepfun": StepFunAdapter,
}

# Friendly aliases -> (provider, model_id)
MODEL_ALIASES: dict[str, tuple[str, str]] = {
    "gpt-4o": ("openai", "gpt-4o"),
    "gpt-4o-mini": ("openai", "gpt-4o-mini"),
    "gpt-4-turbo": ("openai", "gpt-4-turbo"),
    "gpt-3.5-turbo": ("openai", "gpt-3.5-turbo"),
    "claude-3-5-sonnet": ("anthropic", "claude-3-5-sonnet-20240620"),
    "claude-3-opus": ("anthropic", "claude-3-opus-20240229"),
    "claude-3-haiku": ("anthropic", "claude-3-haiku-20240307"),
    "gemini-pro": ("google", "gemini-pro"),
    "gemini-1.5-pro": ("google", "gemini-1.5-pro"),
    "gemini-1.5-flash": ("google", "gemini-1.5-flash"),
    "llama3": ("ollama", "llama3"),
    "llama3-8b": ("ollama", "llama3:8b"),
    "mistral": ("ollama", "mistral"),
    "step-1": ("stepfun", "step-3.5-flash"),
    "step-2": ("stepfun", "step-3.5-flash"),
    "step-3.5-flash": ("stepfun", "step-3.5-flash"),
    "step-3.7-flash": ("stepfun", "step-3.7-flash"),
    "step-router": ("stepfun", "step-router-v1"),
}


# Soft cap on the size of ``ModelRegistry._models``; crossing it logs a warning once.
_MODELS_SOFT_LIMIT = 200


class ModelRegistry:
    """In-memory registry of configured models. Later backed by database."""

    def __init__(self):
        self._models: dict[str, ModelAdapter] = {}
        self._user_keys: dict[str, dict[str, dict[str, str]]] = {}
        self._size_warning_emitted = False

    def register_model(
        self,
        model_id: str,
        provider: str,
        api_key: str,
        base_url: str | None = None,
        capabilities: ModelCapability | None = None,
    ) -> ModelAdapter:
        """Register a model with direct API key."""
        adapter_cls = PROVIDERS.get(provider)
        if not adapter_cls:
            raise ValueError(f"Unknown provider: {provider}. Supported: {list(PROVIDERS.keys())}")

        kwargs: dict[str, Any] = {"model_id": model_id, "api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        if capabilities:
            kwargs["capabilities"] = capabilities

        adapter = adapter_cls(**kwargs)
        key = f"{provider}:{model_id}"
        self._models[key] = adapter
        logger.info("Model registered", provider=provider, model=model_id)
        return adapter

    def get_model(self, provider: str, model_id: str) -> ModelAdapter:
        """Get a registered model."""
        key = f"{provider}:{model_id}"
        adapter = self._models.get(key)
        if not adapter:
            raise ValueError(f"Model not registered: {key}")
        return adapter

    def get_or_create(
        self,
        provider: str,
        model_id: str = "",
        api_key: str = "",
        base_url: str | None = None,
    ) -> ModelAdapter:
        """Get existing model or create new one with user-provided key.

        Supports friendly aliases like ``gpt-4o-mini``. If ``provider`` matches
        an alias key, it is rewritten to the canonical ``(provider, model_id)``.

        Also accepts a single-argument spec form used by the reasoning layer:
        ``get_or_create("openai:gpt-4o-mini")`` or ``get_or_create("step-3.5-flash")``,
        resolving provider/model from MODEL_ALIASES or ``provider:model`` syntax and
        pulling key/base_url from environment variables.
        """
        if not model_id and not api_key:
            return self._resolve_spec(provider)
        resolved_provider, resolved_model = MODEL_ALIASES.get(provider, (provider, model_id))
        if resolved_provider != provider or resolved_model != model_id:
            logger.info(
                "model_alias_resolved",
                alias=f"{provider}:{model_id}",
                resolved=f"{resolved_provider}:{resolved_model}",
            )
        try:
            return self.get_model(resolved_provider, resolved_model)
        except ValueError:
            return self.register_model(resolved_model, resolved_provider, api_key, base_url)

    def _resolve_spec(self, spec: str) -> ModelAdapter:
        """Resolve a single-string alias or ``provider:model`` spec into an adapter.

        Raises ``ValueError`` for an unknown bare spec instead of silently
        inventing an OpenAI model: an unrecognized name is almost always a
        typo, and registering it under the wrong provider hides the mistake.
        """
        if ":" in spec:
            provider, model_id = spec.split(":", 1)
        elif spec in MODEL_ALIASES:
            provider, model_id = MODEL_ALIASES[spec]
        else:
            raise ValueError(
                f"Unknown model spec: {spec!r}. "
                f"Use a provider:model string or one of: {sorted(MODEL_ALIASES)}"
            )
        try:
            return self.get_model(provider, model_id)
        except ValueError:
            from app.core.collaboration.resolver import resolve_api_key, resolve_base_url

            api_key = resolve_api_key(provider, None)
            base_url = resolve_base_url(provider, None)
            return self.register_model(model_id, provider, api_key, base_url)

    def get_default(self) -> ModelAdapter:
        """Return the default model adapter for background reasoning pipelines.

        Uses ``DEFAULT_MODEL_SPEC`` from environment if present; falls back to
        the alias used by chat requests (``gpt-4o``).
        """
        spec = os.environ.get("DEFAULT_MODEL_SPEC") or "gpt-4o"
        return self._resolve_spec(spec)

    def register_keys(
        self,
        provider: str,
        model_id: str,
        api_keys: list[str],
        base_url: str | None = None,
    ) -> None:
        """Register multiple API keys for the same provider/model.

        Creates one adapter per key and stores them under suffixed cache keys
        so key rotation can retrieve adapters for any registered key.
        """
        adapter_cls = PROVIDERS.get(provider)
        if not adapter_cls:
            raise ValueError(f"Unknown provider: {provider}. Supported: {list(PROVIDERS.keys())}")

        for idx, api_key in enumerate(api_keys):
            cache_key = f"{provider}:{model_id}:key:{idx}"
            kwargs: dict[str, Any] = {"model_id": model_id, "api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            adapter = adapter_cls(**kwargs)
            self._models[cache_key] = adapter

        if len(self._models) > _MODELS_SOFT_LIMIT and not self._size_warning_emitted:
            self._size_warning_emitted = True
            logger.warning(
                "model_registry_soft_limit_exceeded",
                count=len(self._models),
                limit=_MODELS_SOFT_LIMIT,
            )
        elif len(self._models) <= _MODELS_SOFT_LIMIT:
            self._size_warning_emitted = False

        logger.info(
            "Multiple keys registered",
            provider=provider,
            model=model_id,
            count=len(api_keys),
        )

    def unregister_key(self, provider: str, model_id: str, idx: int | None = None) -> int:
        """Remove adapters registered via ``register_keys`` for a provider/model.

        Uses the same ``{provider}:{model_id}:key:{idx}`` cache key rule. With
        ``idx`` a single suffixed entry is removed; with ``None`` every suffixed
        entry for the provider/model is removed. Returns the number removed.
        """
        prefix = f"{provider}:{model_id}:key:"
        if idx is not None:
            target = f"{prefix}{idx}"
            if self._models.pop(target, None) is None:
                return 0
            removed = 1
        else:
            stale = [key for key in self._models if key.startswith(prefix)]
            for key in stale:
                del self._models[key]
            removed = len(stale)

        if len(self._models) <= _MODELS_SOFT_LIMIT:
            self._size_warning_emitted = False

        logger.info(
            "Keys unregistered",
            provider=provider,
            model=model_id,
            count=removed,
        )
        return removed

    def list_models(self) -> list[dict[str, Any]]:
        """List all registered models, deduplicated by provider/model.

        ``register_keys`` stores one adapter per rotated API key under
        suffixed cache keys; those all map to the same logical model, so
        only the first instance is reported.
        """
        result = []
        seen: set[tuple[str, str]] = set()
        for adapter in self._models.values():
            provider = adapter.provider
            model_id = adapter.model_id
            key = (provider, model_id)
            if key in seen:
                continue
            seen.add(key)
            caps = adapter.capabilities
            result.append(
                {
                    "provider": provider,
                    "model_id": model_id,
                    "capabilities": caps.model_dump(),
                }
            )
        return result


# Global singleton
registry = ModelRegistry()

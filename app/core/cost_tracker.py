"""Cost tracking for LLM API usage, including per-API-key metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CostEntry:
    provider: str
    model_id: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    session_id: str | None = None


@dataclass
class KeyCostEntry:
    """Token/cost entry attributed to a specific API key."""
    provider: str
    key_prefix: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost: float = 0.0


class CostTracker:
    def __init__(self):
        self.entries: list[CostEntry] = []
        self._key_entries: list[KeyCostEntry] = []

    def record(self, entry: CostEntry) -> None:
        self.entries.append(entry)

    def record_key_usage(
        self,
        provider: str,
        key_prefix: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost: float = 0.0,
    ) -> None:
        """Record token usage and cost for a specific API key.

        """
        self._key_entries.append(
            KeyCostEntry(
                provider=provider,
                key_prefix=key_prefix,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost=cost,
            )
        )

    def get_total_cost(self, provider: str | None = None) -> float:
        if provider:
            return sum(e.cost for e in self.entries if e.provider == provider)
        return sum(e.cost for e in self.entries)

    def get_usage(self, provider: str | None = None) -> dict[str, int]:
        entries = self.entries if not provider else [e for e in self.entries if e.provider == provider]
        return {
            "prompt_tokens": sum(e.prompt_tokens for e in entries),
            "completion_tokens": sum(e.completion_tokens for e in entries),
            "total_tokens": sum(e.total_tokens for e in entries),
        }

    def get_key_stats(self, provider: str, key_prefix: str | None = None) -> dict[str, Any]:
        """Get token usage and cost stats for a provider's keys or a specific key."""
        entries = self._key_entries
        if provider:
            entries = [e for e in entries if e.provider == provider]
        if key_prefix:
            entries = [e for e in entries if e.key_prefix == key_prefix]

        return {
            "tokens_in": sum(e.tokens_in for e in entries),
            "tokens_out": sum(e.tokens_out for e in entries),
            "total_tokens": sum(e.tokens_in + e.tokens_out for e in entries),
            "cost": sum(e.cost for e in entries),
            "request_count": len(entries),
        }

    def get_all_key_stats(self) -> dict[str, Any]:
        """Get token usage stats grouped by provider."""
        result: dict[str, Any] = {}
        providers = {e.provider for e in self._key_entries}
        for provider in providers:
            result[provider] = self.get_key_stats(provider)
        return result


def calculate_cost(provider: str, model_id: str, prompt_tokens: int, completion_tokens: int) -> dict:
    pricing = {
        "openai": {"gpt-4o": 0.005, "gpt-4o-mini": 0.00015, "gpt-3.5-turbo": 0.0005},
        "anthropic": {"claude-3-5-sonnet-20241022": 0.003, "claude-3-opus": 0.015},
        "google": {"gemini-1.5-pro": 0.0035, "gemini-1.5-flash": 0.00035},
        "stepfun": {"step-3.7-flash": 0.001},
    }
    provider_pricing = pricing.get(provider, {})
    rate = provider_pricing.get(model_id, 0.001)
    total_tokens = prompt_tokens + completion_tokens
    total_cost = total_tokens * rate / 1000
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "total_cost": total_cost,
    }


cost_tracker = CostTracker()

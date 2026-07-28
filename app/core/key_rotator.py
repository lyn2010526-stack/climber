"""API key rotation and load balancing for multi-key provider setups.

"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class RotationStrategy(str, Enum):
    """Key selection strategy."""

    ROUND_ROBIN = "round-robin"
    LEAST_BUSY = "least-busy"
    FAILOVER = "failover"


@dataclass
class KeyMetrics:
    """Per-API-key health and usage metrics."""

    key_prefix: str
    api_key: str
    provider: str
    active_requests: int = 0
    success_rate: float = 1.0
    last_error: str | None = None
    last_error_time: float = 0.0
    rate_limit_hits: int = 0
    token_usage: int = 0
    consecutive_failures: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    unhealthy_until: float = 0.0
    backoff_until: float = 0.0

    @property
    def is_healthy(self) -> bool:
        """Key is healthy if not in backoff and cooldown has expired."""
        if time.monotonic() < self.backoff_until:
            return False
        return time.monotonic() >= self.unhealthy_until

    @property
    def error_rate(self) -> float:
        """Fraction of requests that failed."""
        if self.total_requests == 0:
            return 0.0
        return 1.0 - (self.successful_requests / self.total_requests)


@dataclass
class KeyRotationConfig:
    """Configuration for API key rotation."""

    strategy: RotationStrategy = RotationStrategy.LEAST_BUSY
    max_consecutive_failures: int = 3
    cooldown_seconds: float = 60.0
    backoff_multiplier: float = 2.0
    max_backoff_seconds: float = 300.0
    initial_backoff_seconds: float = 1.0


class ApiKeyRotatorError(Exception):
    """Raised when no healthy API keys are available for a provider."""


class ApiKeyRotator:
    """Manages multiple API keys per provider with rotation and load balancing.


    Features:
    - Multiple rotation strategies (round-robin, least-busy, failover)
    - Per-key metrics tracking (success rate, errors, rate limits, tokens)
    - Automatic failover on 401/403/429 errors
    - Exponential backoff for rate-limited keys
    - Health marking after consecutive failures, auto-recovery after cooldown
    """

    def __init__(
        self,
        config: KeyRotationConfig | None = None,
        cost_tracker: Any | None = None,
    ):
        self._config = config or KeyRotationConfig()
        self._cost_tracker = cost_tracker
        self._keys: dict[str, list[KeyMetrics]] = {}
        self._round_robin_index: dict[str, int] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def register_keys(self, provider: str, api_keys: list[str]) -> None:
        """Register multiple API keys for a provider.

        Duplicate key prefixes are ignored.
        """
        if provider not in self._keys:
            self._keys[provider] = []
            self._round_robin_index[provider] = 0
            self._locks[provider] = asyncio.Lock()

        existing_prefixes = {k.key_prefix for k in self._keys[provider]}
        for key in api_keys:
            key_prefix = self._key_prefix(key)
            if key_prefix not in existing_prefixes:
                self._keys[provider].append(
                    KeyMetrics(key_prefix=key_prefix, api_key=key, provider=provider)
                )
                existing_prefixes.add(key_prefix)

        logger.info("Keys registered", provider=provider, count=len(self._keys[provider]))

    def get_key(self, provider: str) -> KeyMetrics | None:
        """Get the next healthy key based on rotation strategy."""
        keys = self._keys.get(provider, [])
        if not keys:
            return None

        healthy_keys = [k for k in keys if k.is_healthy]
        if not healthy_keys:
            return None

        strategy = self._config.strategy

        if strategy == RotationStrategy.ROUND_ROBIN:
            return self._round_robin_select(provider, healthy_keys)
        elif strategy == RotationStrategy.LEAST_BUSY:
            return self._least_busy_select(healthy_keys)
        else:
            return self._failover_select(healthy_keys)

    async def acquire_key(self, provider: str) -> KeyMetrics | None:
        """Acquire a key for making a request (increments active_requests)."""
        key = self.get_key(provider)
        if key is not None:
            key.active_requests += 1
        return key

    def release_key(self, provider: str, key_prefix: str) -> None:
        """Release a key after request completes (decrements active_requests)."""
        for key in self._keys.get(provider, []):
            if key.key_prefix == key_prefix:
                key.active_requests = max(0, key.active_requests - 1)
                break

    def report_success(self, provider: str, key_prefix: str, tokens_used: int = 0) -> None:
        """Report successful request for a key."""
        for key in self._keys.get(provider, []):
            if key.key_prefix == key_prefix:
                key.total_requests += 1
                key.successful_requests += 1
                key.consecutive_failures = 0
                key.token_usage += tokens_used
                if self._cost_tracker:
                    self._cost_tracker.record_key_usage(
                        provider=provider,
                        key_prefix=key_prefix,
                        tokens_in=0,
                        tokens_out=tokens_used,
                        cost=0.0,
                    )
                break

    def report_failure(self, provider: str, key_prefix: str, error: str) -> None:
        """Report failed request for a key."""
        for key in self._keys.get(provider, []):
            if key.key_prefix == key_prefix:
                key.total_requests += 1
                key.consecutive_failures += 1
                key.last_error = error
                key.last_error_time = time.monotonic()

                if key.consecutive_failures >= self._config.max_consecutive_failures:
                    key.unhealthy_until = time.monotonic() + self._config.cooldown_seconds
                    logger.warning(
                        "Key marked unhealthy",
                        provider=provider,
                        key_prefix=key_prefix,
                        consecutive_failures=key.consecutive_failures,
                        cooldown_seconds=self._config.cooldown_seconds,
                    )

                if self._is_rate_limit_error(error):
                    key.rate_limit_hits += 1
                    backoff = min(
                        self._config.initial_backoff_seconds
                        * (self._config.backoff_multiplier ** key.rate_limit_hits),
                        self._config.max_backoff_seconds,
                    )
                    key.backoff_until = time.monotonic() + backoff
                    logger.warning(
                        "Key rate limited, backing off",
                        provider=provider,
                        key_prefix=key_prefix,
                        backoff_seconds=backoff,
                    )
                break

    def report_retry(self, provider: str, key_prefix: str, error: str) -> None:
        """Log that a key was retried with a different key."""
        logger.info(
            "Key retry",
            provider=provider,
            key_prefix=key_prefix,
            error=error[:100],
        )

    def get_key_stats(self, provider: str, key_prefix: str | None = None) -> dict[str, Any]:
        """Get stats for a provider's keys or a specific key."""
        keys = self._keys.get(provider, [])
        if key_prefix:
            for key in keys:
                if key.key_prefix == key_prefix:
                    return self._key_to_dict(key)
            return {}

        return {
            "provider": provider,
            "total_keys": len(keys),
            "healthy_keys": sum(1 for k in keys if k.is_healthy),
            "keys": [self._key_to_dict(k) for k in keys],
        }

    def get_all_stats(self) -> dict[str, Any]:
        """Get stats for all providers."""
        return {provider: self.get_key_stats(provider) for provider in self._keys}

    def _round_robin_select(self, provider: str, keys: list[KeyMetrics]) -> KeyMetrics:
        idx = self._round_robin_index.get(provider, 0)
        selected = keys[idx % len(keys)]
        self._round_robin_index[provider] = (idx + 1) % len(keys)
        return selected

    def _least_busy_select(self, keys: list[KeyMetrics]) -> KeyMetrics:
        return min(keys, key=lambda k: (k.active_requests, k.consecutive_failures))

    def _failover_select(self, keys: list[KeyMetrics]) -> KeyMetrics:
        healthy_sorted = sorted(
            keys,
            key=lambda k: (k.consecutive_failures, k.error_rate, k.active_requests),
        )
        return healthy_sorted[0]

    def _key_prefix(self, api_key: str) -> str:
        """Extract a prefix from an API key for logging (first 8 chars)."""
        return api_key[:8] + "..." if len(api_key) > 8 else api_key

    def _key_to_dict(self, key: KeyMetrics) -> dict[str, Any]:
        return {
            "key_prefix": key.key_prefix,
            "provider": key.provider,
            "active_requests": key.active_requests,
            "total_requests": key.total_requests,
            "successful_requests": key.successful_requests,
            "consecutive_failures": key.consecutive_failures,
            "error_rate": round(key.error_rate, 3),
            "rate_limit_hits": key.rate_limit_hits,
            "token_usage": key.token_usage,
            "is_healthy": key.is_healthy,
            "last_error": key.last_error,
        }

    @staticmethod
    def _is_rate_limit_error(error: str) -> bool:
        """Check if an error is a rate limit / auth error."""
        error_lower = error.lower()
        return (
            "401" in error
            or "403" in error
            or "429" in error
            or "rate limit" in error_lower
            or "unauthorized" in error_lower
            or "forbidden" in error_lower
        )

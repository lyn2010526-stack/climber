"""Cache-first execution for complete non-streaming model responses."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.core import ChatResult
from app.core.long_context.prefix_cache import CacheEntry, PrefixCache
from app.middleware.metrics import record_cache_lookup


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@dataclass(frozen=True)
class CacheRequest:
    key: str
    blocks: tuple[tuple[str, str], ...]
    provider: str
    model_id: str
    input_tokens: int

    @classmethod
    def from_call(
        cls,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        provider: str,
        model_id: str,
        parameters: dict[str, Any] | None = None,
    ) -> CacheRequest:
        fixed_prefix = []
        for message in messages:
            if str(message.get("role")) != "system":
                break
            fixed_prefix.append(message)
        prefix_revision = _digest(_canonical(fixed_prefix))
        blocks = (
            ("prefix_revision", prefix_revision),
            ("tool_schema", _canonical(tools or [])),
            ("model", f"{provider}:{model_id}"),
            ("parameters", _canonical(parameters or {})),
            ("messages", _canonical(messages)),
        )
        encoded = _canonical(blocks)
        return cls(
            key=_digest(encoded),
            blocks=blocks,
            provider=provider,
            model_id=model_id,
            input_tokens=max(1, len(_canonical(messages)) // 4),
        )


class CacheFirstRuntime:
    """Append-only cache with per-key async request coalescing."""

    def __init__(self, cache: PrefixCache | None = None, *, max_flights: int = 256) -> None:
        if max_flights <= 0:
            raise ValueError("max_flights must be positive")
        self.cache = cache or PrefixCache()
        self.max_flights = max_flights
        self._lock = asyncio.Lock()
        self._flights: dict[str, asyncio.Task[ChatResult]] = {}

    @staticmethod
    def _copy_result(result: ChatResult, *, cache_hit: bool) -> ChatResult:
        copied = copy.deepcopy(result)
        copied.cache_hit = cache_hit
        if cache_hit:
            copied._guardrail_processed = False
        return copied

    @staticmethod
    def _is_cacheable(
        result: ChatResult,
        *,
        cancelled: Callable[[], bool],
        require_sanitized: bool,
    ) -> bool:
        return bool(
            result.content
            and not result.tool_calls
            and not getattr(result, "error", None)
            and result.finish_reason in {"stop", "end_turn"}
            and not cancelled()
            and (not require_sanitized or getattr(result, "_guardrail_processed", False))
        )

    async def run(
        self,
        request: CacheRequest,
        producer: Callable[[], Awaitable[ChatResult]],
        *,
        cancelled: Callable[[], bool] = lambda: False,
        require_sanitized: bool = False,
    ) -> ChatResult:
        entry = self.cache.lookup(request.key)
        if entry is not None:
            record_cache_lookup(request.provider, request.model_id, hit=True, tokens=entry.input_tokens)
            return self._copy_result(entry.value, cache_hit=True)

        owner = False
        bypass_cache = False
        flight: asyncio.Task[ChatResult] | None = None
        async with self._lock:
            entry = self.cache.lookup(request.key)
            if entry is not None:
                record_cache_lookup(request.provider, request.model_id, hit=True, tokens=entry.input_tokens)
                return self._copy_result(entry.value, cache_hit=True)
            flight = self._flights.get(request.key)
            if flight is None:
                self.cache.record_stale(request.blocks)
                record_cache_lookup(request.provider, request.model_id, hit=False, tokens=0)
                if len(self._flights) >= self.max_flights:
                    bypass_cache = True
                else:
                    flight = asyncio.create_task(
                        self._produce(
                            request,
                            producer,
                            cancelled=cancelled,
                            require_sanitized=require_sanitized,
                        )
                    )
                    flight.add_done_callback(lambda done: done.exception() if not done.cancelled() else None)
                    self._flights[request.key] = flight
                    owner = True

        if bypass_cache:
            return self._copy_result(await producer(), cache_hit=False)
        if flight is None:  # pragma: no cover - guarded by the lock branches above
            raise RuntimeError("cache flight was not initialized")

        result = await asyncio.shield(flight)
        if not owner:
            shared_entry = self.cache.lookup(request.key)
            hit = shared_entry is not None
            record_cache_lookup(
                request.provider,
                request.model_id,
                hit=hit,
                tokens=shared_entry.input_tokens if shared_entry is not None else 0,
            )
            return self._copy_result(result, cache_hit=hit)
        return self._copy_result(result, cache_hit=False)

    async def _produce(
        self,
        request: CacheRequest,
        producer: Callable[[], Awaitable[ChatResult]],
        *,
        cancelled: Callable[[], bool],
        require_sanitized: bool,
    ) -> ChatResult:
        try:
            result = await producer()
            if self._is_cacheable(
                result,
                cancelled=cancelled,
                require_sanitized=require_sanitized,
            ):
                stored = self._copy_result(result, cache_hit=False)
                self.cache.append(
                    CacheEntry(
                        key=request.key,
                        blocks=request.blocks,
                        value=stored,
                        input_tokens=request.input_tokens,
                    )
                )
            return self._copy_result(result, cache_hit=False)
        finally:
            async with self._lock:
                current = asyncio.current_task()
                if self._flights.get(request.key) is current:
                    self._flights.pop(request.key, None)

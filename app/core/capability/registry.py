"""Capability registry + automatic routing.

All installed capabilities register here. When the agent asks for a
capability, the registry picks the best implementation by:
  1. prerequisite satisfaction (is it executable now?)
  2. highest historical success rate
  3. lowest estimated cost (latency + tokens + money weighted)
  4. user preference (e.g. "prefer local")

On failure it automatically falls back to the next candidate (max 3 distinct
implementations). The same capability id may have multiple implementations.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from app.core.capability.capability import Capability, CapabilityStats

logger = structlog.get_logger()

MAX_FALLBACKS = 3


class NoExecutableCapability(RuntimeError):
    """Raised when no registered implementation is executable for a capability."""


class CapabilityRegistry:
    """Registry of capability implementations with automatic routing."""

    def __init__(self, max_fallbacks: int = MAX_FALLBACKS) -> None:
        self._implementations: dict[str, list[Capability]] = {}
        self._stats: dict[str, dict[str, CapabilityStats]] = {}
        self._user_preferences: dict[str, str] = {}
        self._max_fallbacks = max_fallbacks

    # ── registration ──

    def register(self, capability: Capability) -> None:
        cid = capability.meta.id
        self._implementations.setdefault(cid, []).append(capability)
        self._stats.setdefault(cid, {})[id(capability)] = CapabilityStats()

    def unregister(self, capability_id: str, implementation: Capability | None = None) -> bool:
        impls = self._implementations.get(capability_id)
        if not impls:
            return False
        if implementation is None:
            self._implementations.pop(capability_id, None)
            self._stats.pop(capability_id, None)
            return True
        if implementation in impls:
            impls.remove(implementation)
            self._stats.get(capability_id, {}).pop(id(implementation), None)
            return True
        return False

    def list_capabilities(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for cid, impls in self._implementations.items():
            result.append({
                "id": cid,
                "name": impls[0].meta.name if impls else cid,
                "description": impls[0].meta.description if impls else "",
                "implementations": len(impls),
            })
        return result

    def get_implementations(self, capability_id: str) -> list[Capability]:
        return self._implementations.get(capability_id, [])

    # ── user preference ──

    def set_user_preference(self, capability_id: str, impl_hint: str) -> None:
        """e.g. preference 'local' biases toward local implementations."""
        self._user_preferences[capability_id] = impl_hint

    # ── routing ──

    def _rank(self, capability_id: str, implementations: list[Capability]) -> list[Capability]:
        preference = self._user_preferences.get(capability_id, "")
        scored: list[tuple[float, Capability]] = []
        for impl in implementations:
            stats = self._stats.get(capability_id, {}).get(id(impl), CapabilityStats())
            success_score = stats.success_rate if stats.use_count else 0.5
            cost = impl.meta.cost_profile
            cost_score = 1.0 / (1.0 + float(cost.get("estimated_ms", 100)) / 1000.0)
            preference_bonus = 1.0 if preference and preference in impl.meta.id else 0.0
            score = success_score * 0.5 + cost_score * 0.3 + preference_bonus * 0.2
            scored.append((score, impl))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [impl for _, impl in scored]

    async def execute(self, capability_id: str, **kwargs: Any) -> Any:
        """Execute the best implementation, falling back automatically."""
        impls = self.get_implementations(capability_id)
        if not impls:
            raise NoExecutableCapability(f"no implementation registered for '{capability_id}'")

        ranked = self._rank(capability_id, impls)
        last_error: Exception | None = None
        attempted = 0

        for impl in ranked:
            if attempted >= self._max_fallbacks:
                break
            if not impl.is_executable():
                continue
            attempted += 1
            start = time.monotonic()
            try:
                result = await impl.execute(**kwargs)
                elapsed = (time.monotonic() - start) * 1000
                self._record(capability_id, impl, success=True, ms=elapsed)
                return result
            except Exception as exc:
                elapsed = (time.monotonic() - start) * 1000
                self._record(capability_id, impl, success=False, ms=elapsed)
                last_error = exc
                logger.warning(
                    "capability.fallback",
                    capability_id=capability_id,
                    impl=impl.meta.id,
                    error=str(exc),
                )

        if last_error is not None:
            raise last_error
        raise NoExecutableCapability(f"no executable implementation for '{capability_id}'")

    def _record(self, capability_id: str, impl: Capability, success: bool, ms: float) -> None:
        stats = self._stats.setdefault(capability_id, {}).setdefault(
            id(impl), CapabilityStats()
        )
        stats.use_count += 1
        if success:
            stats.success_count += 1
        else:
            stats.fail_count += 1
        stats.total_ms += ms

    # ── stats / evolution feed ──

    def stats(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for cid, impls in self._implementations.items():
            result[cid] = {}
            for impl in impls:
                stats = self._stats.get(cid, {}).get(id(impl), CapabilityStats())
                result[cid][impl.meta.id] = {
                    "use_count": stats.use_count,
                    "success_rate": stats.success_rate,
                    "avg_ms": stats.avg_ms,
                }
        return result


_default_registry: CapabilityRegistry | None = None


def get_capability_registry() -> CapabilityRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = CapabilityRegistry()
    return _default_registry

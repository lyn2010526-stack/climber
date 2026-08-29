"""Capability evolution — each call is recorded, and capabilities under 60%
success rate are automatically flagged for optimization.
"""

from __future__ import annotations

from typing import Any

from app.core.capability.registry import CapabilityRegistry


class CapabilityEvolution:
    """Tracks capability usage and auto-identifies underperformers."""

    def __init__(self, registry: CapabilityRegistry, threshold: float = 0.6) -> None:
        self._registry = registry
        self._threshold = threshold
        self._needs_optimization: set[str] = set()

    def evaluate(self) -> list[dict[str, Any]]:
        flagged: list[dict[str, Any]] = []
        for cid in self._registry.list_capabilities():
            impls = self._registry.get_implementations(cid["id"])
            for impl in impls:
                stats = impl.stats()
                if stats.use_count >= 3 and stats.success_rate < self._threshold:
                    self._needs_optimization.add(cid["id"])
                    flagged.append({
                        "id": cid["id"],
                        "name": cid.get("name", ""),
                        "success_rate": stats.success_rate,
                        "use_count": stats.use_count,
                    })
        return flagged

    def needs_optimization(self) -> list[str]:
        return list(self._needs_optimization)

    def mark_optimized(self, cap_id: str) -> None:
        self._needs_optimization.discard(cap_id)

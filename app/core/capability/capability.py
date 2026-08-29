"""Unified Capability abstraction.

Every capability (whether it comes from a local tool, MCP server, skill,
HTTP API, subagent, model call, or perception layer) is described by the same
interface. The agent never needs to know where a capability comes from.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CapabilityMeta:
    """Static metadata that all capabilities must declare."""

    id: str
    name: str
    description: str
    capability_type: str  # tool | mcp | skill | http | subagent | model | perception
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    cost_profile: dict[str, Any] = field(default_factory=lambda: {
        "estimated_ms": 100,
        "estimated_tokens": 0,
        "estimated_cost": 0.0,
    })
    prerequisites: list[str] = field(default_factory=list)  # e.g. "root", "android_10+"
    side_effects: list[str] = field(default_factory=list)  # e.g. "modifies_screen", "network_access"
    version: str = "1.0.0"
    author: str = ""


@dataclass
class CapabilityStats:
    """Runtime usage statistics for a capability."""

    use_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    total_ms: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.use_count == 0:
            return 0.0
        return self.success_count / self.use_count

    @property
    def avg_ms(self) -> float:
        if self.use_count == 0:
            return 0.0
        return self.total_ms / self.use_count


class Capability(ABC):
    """Abstract base for all capabilities."""

    @property
    @abstractmethod
    def meta(self) -> CapabilityMeta:
        ...

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        ...

    @abstractmethod
    def is_executable(self) -> bool:
        """Return True when all prerequisites are satisfied right now."""
        ...

    def stats(self) -> CapabilityStats:
        return CapabilityStats()


class WrappedCapability(Capability):
    """Wraps an arbitrary callable as a Capability.

    Useful for quickly wrapping Python functions without a full subclass.
    """

    def __init__(
        self,
        meta: CapabilityMeta,
        fn: Callable[..., Any],
        executable_check: Callable[[], bool] = lambda: True,
    ) -> None:
        self._meta = meta
        self._fn = fn
        self._executable_check = executable_check

    @property
    def meta(self) -> CapabilityMeta:
        return self._meta

    async def execute(self, **kwargs: Any) -> Any:
        result = self._fn(**kwargs)
        if hasattr(result, "__await__"):
            return await result
        return result

    def is_executable(self) -> bool:
        return self._executable_check()

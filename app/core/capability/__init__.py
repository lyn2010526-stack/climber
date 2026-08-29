"""Unified Capability abstraction."""

from app.core.capability.adapters import (
    HttpCapability,
    McpCapability,
    ModelCapability,
    PerceptionCapability,
    SkillCapability,
    SubagentCapability,
)
from app.core.capability.capability import (
    Capability,
    CapabilityMeta,
    CapabilityStats,
    WrappedCapability,
)
from app.core.capability.evolution import CapabilityEvolution
from app.core.capability.market import (
    CapabilityMarket,
    CapabilityPackage,
    get_capability_market,
)
from app.core.capability.registry import (
    CapabilityRegistry,
    NoExecutableCapability,
    get_capability_registry,
)

__all__ = [
    "Capability",
    "CapabilityEvolution",
    "CapabilityMarket",
    "CapabilityMeta",
    "CapabilityPackage",
    "CapabilityRegistry",
    "CapabilityStats",
    "HttpCapability",
    "McpCapability",
    "ModelCapability",
    "NoExecutableCapability",
    "PerceptionCapability",
    "SkillCapability",
    "SubagentCapability",
    "WrappedCapability",
    "get_capability_market",
    "get_capability_registry",
]

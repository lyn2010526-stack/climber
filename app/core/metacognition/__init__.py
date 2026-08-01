"""Metacognition subsystem — self-monitoring, simulation, and evolution."""

from __future__ import annotations

from app.core.metacognition.monitor import MetaCognitionMonitor
from app.core.metacognition.hypothesis import HypothesisSimulator
from app.core.metacognition.causal import CausalAttribution
from app.core.metacognition.resource import ResourceOrchestrator
from app.core.metacognition.orchestrator import MetacognitionOrchestrator, ExecutionContext
from app.core.metacognition.capability_discovery import CapabilityDiscovery
from app.core.metacognition.self_refactor import SelfModuleRefactor
from app.core.metacognition.goal_adjuster import GoalDynamicAdjuster
from app.core.metacognition.sub_agent import SubAgentOrchestrator
from app.core.metacognition.memory_pruner import LongTermMemoryPruner

__all__ = [
    "MetaCognitionMonitor",
    "HypothesisSimulator",
    "CausalAttribution",
    "ResourceOrchestrator",
    "MetacognitionOrchestrator",
    "CapabilityDiscovery",
    "SelfModuleRefactor",
    "GoalDynamicAdjuster",
    "SubAgentOrchestrator",
    "LongTermMemoryPruner",
]

"""Metacognition subsystem — self-monitoring, simulation, and evolution."""

from __future__ import annotations

from app.core.metacognition.capability_discovery import CapabilityDiscovery
from app.core.metacognition.causal import CausalAttribution, CausalGraph
from app.core.metacognition.goal_adjuster import GoalDynamicAdjuster
from app.core.metacognition.hypothesis import HypothesisBelief, HypothesisSimulator, WorldState
from app.core.metacognition.judgment import (
    Judgment,
    aggregate_dissent,
    calibrate,
    continuous_goal,
    deflate_verdict,
)
from app.core.metacognition.memory_pruner import LongTermMemoryPruner
from app.core.metacognition.monitor import MetaCognitionMonitor
from app.core.metacognition.orchestrator import ExecutionContext, MetacognitionCycleResult, MetacognitionOrchestrator
from app.core.metacognition.resource import ResourceOrchestrator
from app.core.metacognition.safety_gate import (
    BLOCK_THRESHOLD,
    DEFAULT_HALF_LIFE_DAYS,
    DEFAULT_SURVIVAL_THRESHOLD,
    MAX_CONSECUTIVE_BOOSTS,
    SafetyVerdict,
    coupled_decay,
    damped_boost,
    gated_fitness,
    screen,
)
from app.core.metacognition.self_refactor import SelfModuleRefactor
from app.core.metacognition.sub_agent import SubAgentOrchestrator

__all__ = [
    "BLOCK_THRESHOLD",
    "DEFAULT_HALF_LIFE_DAYS",
    "DEFAULT_SURVIVAL_THRESHOLD",
    "MAX_CONSECUTIVE_BOOSTS",
    "CapabilityDiscovery",
    "CausalAttribution",
    "CausalGraph",
    "ExecutionContext",
    "GoalDynamicAdjuster",
    "HypothesisSimulator",
    "HypothesisBelief",
    "Judgment",
    "LongTermMemoryPruner",
    "MetaCognitionMonitor",
    "MetacognitionOrchestrator",
    "MetacognitionCycleResult",
    "ResourceOrchestrator",
    "SafetyVerdict",
    "SelfModuleRefactor",
    "SubAgentOrchestrator",
    "WorldState",
    "aggregate_dissent",
    "calibrate",
    "continuous_goal",
    "coupled_decay",
    "damped_boost",
    "deflate_verdict",
    "gated_fitness",
    "screen",
]

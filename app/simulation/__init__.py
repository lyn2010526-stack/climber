"""Simulation experiment harness (science-agent orchestration loop)."""

from __future__ import annotations

from app.simulation.adjuster import AdjustConfig, ParameterAdjuster
from app.simulation.harness import HarnessOptions, HarnessRunResult, SimulationHarness
from app.simulation.ledger import ExperimentLedger
from app.simulation.llm_planner import LLMExperimentPlanner
from app.simulation.llm_reviewer import LLMReviewer
from app.simulation.models import (
    ExperimentAttempt,
    ExperimentReport,
    ExperimentSpec,
    Verdict,
)
from app.simulation.orchestrator import (
    AggregateReviewContext,
    OrchestratorOptions,
    OrchestratorResult,
    PlanRound,
    ScienceSimulationAgent,
)
from app.simulation.planner import (
    ExperimentPlan,
    ParamDim,
    plan_from_schema,
    plan_to_json,
)
from app.simulation.probes import (
    detect_divergence,
    detect_error,
    extract_numbers,
    probe_convergence,
)
from app.simulation.review import (
    HarnessReviewer,
    ParameterPolicy,
    ReviewContext,
    metrics_from_report,
)

__all__ = [
    "AdjustConfig",
    "AggregateReviewContext",
    "ExperimentAttempt",
    "ExperimentLedger",
    "ExperimentPlan",
    "ExperimentReport",
    "ExperimentSpec",
    "HarnessOptions",
    "HarnessReviewer",
    "HarnessRunResult",
    "LLMExperimentPlanner",
    "LLMReviewer",
    "OrchestratorOptions",
    "OrchestratorResult",
    "ParamDim",
    "ParameterAdjuster",
    "ParameterPolicy",
    "PlanRound",
    "ReviewContext",
    "ScienceSimulationAgent",
    "SimulationHarness",
    "Verdict",
    "detect_divergence",
    "detect_error",
    "extract_numbers",
    "metrics_from_report",
    "plan_from_schema",
    "plan_to_json",
    "probe_convergence",
]
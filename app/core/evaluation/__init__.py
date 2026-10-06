"""Evaluation environment for AI agent trajectories.

Implements the evaluation methodology from the agent-evaluation chapter:
scenario dataset, trajectory capture, rubric scoring with per-item
verdicts, pass@k / pass^k aggregation, baseline regression detection,
and an LLM-as-a-Judge hook.
"""

from app.core.evaluation.baseline import (
    compare_to_baseline,
    load_baseline,
    report_to_baseline,
    save_baseline,
)
from app.core.evaluation.judges import (
    DEFAULT_JUDGE,
    DeterministicJudge,
    LLMRubricJudge,
)
from app.core.evaluation.models import (
    CallRecord,
    EvalScenario,
    EvaluationReport,
    EvaluationResult,
    ItemVerdict,
    RubricItem,
    ScenarioReport,
    Trajectory,
)
from app.core.evaluation.report_store import REPORT_STORE, ReportStore
from app.core.evaluation.runner import (
    evaluate_trajectory,
    make_engine_agent_fn,
    pass_at_k,
    pass_hat_k,
    run_evaluation,
)
from app.core.evaluation.scenarios import (
    builtin_scenarios,
    load_scenarios,
    scenarios_from_dict,
)

__all__ = [
    "DEFAULT_JUDGE",
    "REPORT_STORE",
    "CallRecord",
    "DeterministicJudge",
    "EvalScenario",
    "EvaluationReport",
    "EvaluationResult",
    "ItemVerdict",
    "LLMRubricJudge",
    "ReportStore",
    "RubricItem",
    "ScenarioReport",
    "Trajectory",
    "builtin_scenarios",
    "compare_to_baseline",
    "evaluate_trajectory",
    "load_baseline",
    "load_scenarios",
    "make_engine_agent_fn",
    "pass_at_k",
    "pass_hat_k",
    "report_to_baseline",
    "run_evaluation",
    "save_baseline",
    "scenarios_from_dict",
]

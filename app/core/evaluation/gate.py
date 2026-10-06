"""Explicit boundary/retention validation gate; never activates a proposal itself."""

from app.core.evaluation.baseline import compare_to_baseline
from app.core.evaluation.runner import run_evaluation


async def evaluate_proposal(
    boundary, retention, agent_fn, *, retention_baseline, judge=None, **run_options
):
    if not boundary or not retention or not retention_baseline.get("scores"):
        raise ValueError("boundary, retention and a retention baseline are required")
    boundary_report = await run_evaluation(boundary, agent_fn, judge, **run_options)
    retention_report = await run_evaluation(retention, agent_fn, judge, **run_options)
    regression = compare_to_baseline(retention_report, retention_baseline)
    accepted = (
        all(result.passed for scenario in boundary_report.scenarios for result in scenario.results)
        and all(
            result.passed for scenario in retention_report.scenarios for result in scenario.results
        )
        and not regression["regressed"]
    )
    return {
        "accepted": accepted,
        "boundary": boundary_report.to_dict(),
        "retention": retention_report.to_dict(),
        "regression": regression,
    }

"""Trajectory regression: persist score baselines as JSON and compare runs.

A baseline is a compact snapshot of one report (per-scenario best score
plus average). A new run regresses when a scenario score or the average
drops more than the threshold below the baseline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.evaluation.models import EvaluationReport


def report_to_baseline(report: EvaluationReport) -> dict[str, Any]:
    """Compact baseline snapshot from a report."""
    return report.to_baseline()


def save_baseline(report: EvaluationReport, path: str | Path) -> dict[str, Any]:
    """Write a baseline JSON file for a report and return the snapshot."""
    baseline = report.to_baseline()
    target = Path(path)
    if target.parent and not target.parent.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(baseline, handle, ensure_ascii=False, indent=2)
    return baseline


def load_baseline(path: str | Path) -> dict[str, Any]:
    """Load a baseline JSON file."""
    with open(path, encoding="utf-8") as handle:
        loaded: dict[str, Any] = json.load(handle)
        return loaded


def compare_to_baseline(
    report: EvaluationReport,
    baseline: dict[str, Any],
    threshold: float = 0.05,
) -> dict[str, Any]:
    """Compare a fresh report against a baseline and flag regressions.

    A regression means a score dropped below the baseline by more than
    ``threshold``. Scenario entries missing from the baseline are marked
    as new; baseline entries missing from the report are dropped scenarios.
    """
    current = report.to_baseline()
    if threshold < 0:
        raise ValueError("threshold must be non-negative")
    scenario_rows: list[dict[str, Any]] = []
    for scenario_id, base_score in (baseline.get("scores") or {}).items():
        if scenario_id in current["scores"]:
            score = current["scores"][scenario_id]
            delta = score - base_score
            scenario_rows.append(
                {
                    "scenario_id": scenario_id,
                    "baseline_score": base_score,
                    "current_score": score,
                    "delta": round(delta, 4),
                    "regression": delta < -threshold
                    or (
                        baseline.get("passes", {}).get(scenario_id, False)
                        and not current["passes"].get(scenario_id, False)
                    ),
                }
            )
        else:
            scenario_rows.append(
                {
                    "scenario_id": scenario_id,
                    "baseline_score": base_score,
                    "current_score": None,
                    "delta": None,
                    "regression": True,
                    "note": "scenario missing from current run",
                }
            )
    baseline_average = baseline.get("average_score", 0.0)
    overall_delta = current["average_score"] - baseline_average
    overall_regression = overall_delta < -threshold
    return {
        "threshold": threshold,
        "overall": {
            "baseline_score": baseline_average,
            "current_score": current["average_score"],
            "delta": round(overall_delta, 4),
            "regression": overall_regression,
        },
        "scenarios": scenario_rows,
        "regressed": overall_regression or any(row["regression"] for row in scenario_rows),
    }

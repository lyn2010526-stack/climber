"""Convergence and plausibility probes for simulation tool output.

Implements the openfoam-agent style judgment: parse the tool's text
result, detect divergence markers (NaN, Inf, "diverged", "blowing up",
"error", "failed to converge"), extract numeric metrics, and flag empty
or malformed outputs so the orchestrator can auto-retry instead of
accepting garbage.
"""

from __future__ import annotations

import math
import json
import re
from typing import Any

from app.simulation.models import ProbeResult

DIVERGENCE_MARKERS = (
    "nan",
    "-nan",
    "inf",
    "infinity",
    "diverged",
    "divergence",
    "blowing up",
    "blow up",
    "not converged",
    "failed to converge",
    "did not converge",
    "unstable",
    "floating point exception",
    "segmentation fault",
    "crashed",
    "timed out",
    "timeout",
)

ERROR_MARKERS = (
    "error",
    "exception",
    "traceback",
    "invalid",
    "failed",
    "aborted",
)

_NUMBER_RE = re.compile(
    r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
)


def extract_numbers(text: str) -> list[float]:
    """Extract all numeric values from a text output in order."""
    if not text:
        return []
    return [float(m) for m in _NUMBER_RE.findall(text)]


def detect_divergence(text: str) -> bool:
    """Return True if the output contains divergence indicators."""
    if not text:
        return False
    lowered = text.lower()
    return any(marker in lowered for marker in DIVERGENCE_MARKERS)


def detect_error(text: str) -> bool:
    """Return True if the output looks like an error/exception dump."""
    if not text:
        return False
    lowered = text.lower()
    hits = sum(1 for marker in ERROR_MARKERS if marker in lowered)
    return hits >= 2


def find_metric(metrics: dict[str, Any], candidates: list[str]) -> float | None:
    """Return the first numeric metric matching any candidate key."""
    for key in candidates:
        for mkey, value in metrics.items():
            if key.lower() in mkey.lower():
                try:
                    return float(value)
                except (TypeError, ValueError):
                    continue
    return None


def probe_convergence(
    output: str,
    *,
    expect_numbers: bool = False,
    metric_keys: list[str] | None = None,
    metrics: dict[str, Any] | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    reject_nan: bool = True,
) -> ProbeResult:
    """Run plausibility probes on a tool result.

    Returns an ``ok=False`` ProbeResult when the output shows divergence,
    an error dump, is empty when numbers were expected, or contains values
    outside the declared bounds. ``metrics`` is populated with any extracted
    named metrics plus the raw numeric list.
    """
    if not output or not output.strip():
        return ProbeResult(
            ok=False,
            reason="empty tool output",
        )

    if detect_divergence(output):
        return ProbeResult(
            ok=False,
            reason="divergence marker detected in output",
        )

    if detect_error(output):
        return ProbeResult(
            ok=False,
            reason="error/exception markers detected in output",
        )

    parsed_metrics = dict(metrics or {})
    if not parsed_metrics:
        try:
            parsed = json.loads(output)
        except (json.JSONDecodeError, TypeError):
            parsed = None
        if isinstance(parsed, dict):
            parsed_metrics = parsed

    numbers = extract_numbers(output)
    for value in parsed_metrics.values():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            numbers.append(float(value))
    if reject_nan and any(math.isnan(n) or math.isinf(n) for n in numbers):
        return ProbeResult(
            ok=False,
            reason="NaN/Inf value present in output",
        )

    if expect_numbers and not numbers:
        return ProbeResult(
            ok=False,
            reason="expected numeric output but none found",
        )

    if min_value is not None and numbers and min(numbers) < min_value:
        return ProbeResult(ok=False, reason=f"value below min bound {min_value}")

    if max_value is not None and numbers and max(numbers) > max_value:
        return ProbeResult(ok=False, reason=f"value above max bound {max_value}")

    result_metrics: dict[str, Any] = dict(parsed_metrics)
    result_metrics["numbers"] = numbers
    if metric_keys:
        for key in metric_keys:
            value = find_metric(result_metrics, [key])
            if value is not None:
                result_metrics[key] = value

    return ProbeResult(ok=True, reason="probes passed", metrics=result_metrics)

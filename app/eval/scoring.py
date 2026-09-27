"""Reduction from target evidence to a score table.

This module is the only place a score is computed, and it computes one only from
a :class:`~app.eval.types.TargetRunResult` that a target produced by actually
running. The rules, in order:

1. Cases the target reports as :data:`Verdict.INCONCLUSIVE`, or omits entirely
   while also reporting an inconclusive run, become inconclusive rows with a
   reason and **no score**.
2. A run the target could not measure at all becomes an all-inconclusive table
   whose aggregate score and pass rate are ``None``.
3. When the evidence carries coverage gaps, a run-wide inconclusive reason is
   recorded so a consumer cannot read the aggregate as a complete measurement.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.eval.types import (
    CaseRow,
    Evidence,
    RunStatus,
    ScoreTable,
    TargetRunResult,
    Verdict,
    capability_from_mapping,
)

# A case measured as passing scores 1.0 and a measured failure scores 0.0. These
# come from the target's own boolean verdict, so they are a projection of a
# measurement rather than a default. Targets with a continuous metric supply the
# score through ``scoring_method`` instead.
PASSED_SCORE = 1.0
FAILED_SCORE = 0.0

UNKNOWN_CASE_REASON = "no evidence covered this case; it was never measured"
PENDING_RUN_REASON = "the run did not finish; the case has no terminal verdict"


def fingerprint_for(target: str, inputs: dict[str, Any]) -> str:
    """Stable digest of the inputs that decide a run's outcome."""
    payload = json.dumps({"target": target, "inputs": inputs}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _reason_for(result: TargetRunResult, case_id: str) -> str:
    reason = str(result.reasons.get(case_id) or "").strip()
    if reason:
        return reason
    if result.inconclusive and result.message:
        return result.message
    return PENDING_RUN_REASON if result.verdicts else UNKNOWN_CASE_REASON


def build_rows(result: TargetRunResult) -> list[CaseRow]:
    """Turn target verdicts into score-table rows, preserving inconclusive."""
    case_ids = set(result.verdicts) | set(result.reasons)
    rows: list[CaseRow] = []
    for case_id in sorted(case_ids):
        verdict = result.verdicts.get(case_id, Verdict.INCONCLUSIVE)
        if not verdict.is_scored:
            rows.append(
                CaseRow(
                    case_id=case_id,
                    verdict=Verdict.INCONCLUSIVE,
                    score=None,
                    reason=_reason_for(result, case_id) or UNKNOWN_CASE_REASON,
                    scoring_method="inconclusive",
                )
            )
            continue
        rows.append(
            CaseRow(
                case_id=case_id,
                verdict=verdict,
                score=PASSED_SCORE if verdict is Verdict.PASSED else FAILED_SCORE,
                reason=str(result.reasons.get(case_id) or ""),
                scoring_method="arcbench_acceptance_spec",
            )
        )
    return rows


def build_evidence(result: TargetRunResult, fingerprint: str, workdir: str = "") -> Evidence:
    """Collect the reproduction record from a target result.

    The preflight snapshot lives in the evidence payload as well as on the
    result, so a table rebuilt from stored evidence still reports which
    capabilities were present when the measurement was taken.
    """
    stored_capabilities = capability_from_mapping(result.evidence.get("capabilities"))
    return Evidence(
        fingerprint=fingerprint or fingerprint_for(result.target, {}),
        target=result.target,
        inputs=dict(result.evidence.get("inputs") or {}),
        preflight=list(result.capabilities) or stored_capabilities,
        summary=dict(result.evidence.get("summary") or {}),
        arc_events=[e for e in (result.evidence.get("arc_events") or []) if isinstance(e, dict)],
        workdir=workdir or str(result.evidence.get("workdir") or ""),
    )


def build_score_table(
    result: TargetRunResult,
    *,
    run_id: str = "",
    fingerprint: str = "",
    workdir: str = "",
) -> ScoreTable:
    """Reduce a target result into the reproducible score table."""
    rows = build_rows(result)
    scored = [row for row in rows if row.verdict.is_scored]

    status = RunStatus.INCONCLUSIVE if not scored else RunStatus.MEASURED

    reasons: list[str] = []
    if result.inconclusive and result.message:
        reasons.append(result.message)
    for check in result.capabilities:
        if check.blocking:
            reasons.append(f"{check.name}: {check.detail}".rstrip(": "))
    for row in rows:
        if row.is_inconclusive and row.reason:
            reasons.append(f"{row.case_id}: {row.reason}")

    if result.inconclusive and not result.message and not reasons:
        reasons.append("target reported an inconclusive run without a reason")

    deduped: list[str] = []
    for reason in reasons:
        if reason and reason not in deduped:
            deduped.append(reason)

    message = result.message
    if not message:
        if status is RunStatus.INCONCLUSIVE:
            message = "the run produced no usable measurement; every case is inconclusive"
        else:
            gaps = len(rows) - len(scored)
            message = f"{len(scored)}/{len(rows)} cases backed by evidence"
            if gaps:
                message += f"; {gaps} inconclusive"

    return ScoreTable(
        run_id=run_id,
        target=result.target,
        status=status,
        rows=rows,
        inconclusive_reasons=deduped,
        evidence=build_evidence(result, fingerprint, workdir),
        message=message,
    )


def score_table_from_stored(
    run_id: str,
    result: TargetRunResult,
    *,
    fingerprint: str = "",
    workdir: str = "",
) -> ScoreTable:
    """Recompute a score table from a stored target result.

    This is the reproducibility path: a run read back from storage is reduced
    from its evidence with the same code that produced the original table, so
    the two agree by construction rather than by copying stored numbers.
    """
    return build_score_table(result, run_id=run_id, fingerprint=fingerprint, workdir=workdir)

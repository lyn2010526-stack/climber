"""Persistence for the evaluation runtime, against the existing eval tables.

The schema in ``app/storage/models_eval.py`` predates this runtime and cannot
express a missing measurement: every numeric column is ``NOT NULL``. Rather than
lie to those columns, this module keeps a single authoritative representation of
each case in ``EvalRun.results_json`` where the score is genuinely nullable, and
uses ``EvalResult`` for the per-case rows that were actually measured.

The consequences are deliberate and are covered by tests:

- ``EvalRun.average_score`` and ``EvalRun.pass_rate`` are written only when at
  least one case was scored. An unmeasured run stores ``0.0``, which is
  indistinguishable from a real zero, so readers must use
  ``EvalRun.results_json``; :func:`load_score_table` reconstructs the honest
  view and :attr:`~app.eval.types.ScoreTable.score` is ``None`` there.
- An inconclusive ``EvalResult`` is not a failed ``EvalResult``. It is written
  with ``scoring_method='inconclusive'`` and its verdict carried in
  ``reasoning``, so no aggregate over the table can silently count it.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.eval.errors import EvaluationError
from app.eval.scoring import fingerprint_for, score_table_from_stored
from app.eval.types import ScoreTable, TargetRunResult, Verdict
from app.storage.models_eval import EvalDataset, EvalResult, EvalRun

# ``EvalResult.scoring_method`` is a 30-char column, so the method names the
# runtime stores must stay short. The per-case verdict also travels in
# ``reasoning`` because the schema has no verdict column.
METHOD_INCONCLUSIVE = "inconclusive"
METHOD_ARCBENCH = "arcbench_spec"
MAX_METHOD_LENGTH = 30


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _clamp_method(method: str) -> str:
    return _truncate(str(method or METHOD_ARCBENCH), MAX_METHOD_LENGTH)


def _load_json(text: str) -> Any:
    try:
        return json.loads(text or "null")
    except ValueError:
        return None


async def ensure_dataset(
    db: AsyncSession,
    *,
    user_id: str,
    name: str,
    description: str,
    case_count: int,
    data: list[Any] | None = None,
) -> EvalDataset:
    """Create the dataset row that describes what was evaluated.

    The dataset holds the target's own case definitions, so a stored run points
    at the inputs it was measured against rather than at an opaque id.
    """
    payload = json.dumps(data or [], default=str)
    dataset = EvalDataset(
        user_id=user_id,
        name=_truncate(name, 200),
        description=description,
        case_count=int(case_count),
        data_json=payload,
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    return dataset


async def persist_score_table(
    db: AsyncSession,
    *,
    table: ScoreTable,
    user_id: str,
    dataset_id: str,
    agent_id: str,
) -> EvalRun:
    """Store a score table plus one row per evaluated case.

    ``results_json`` carries the full score table so the run can be re-read and
    recomputed without re-executing anything.
    """
    run = EvalRun(
        id=str(uuid4()),
        user_id=user_id,
        dataset_id=dataset_id,
        agent_id=agent_id,
        total_cases=table.total_cases,
        passed_cases=table.passed_cases,
        failed_cases=table.failed_cases,
        average_score=table.score if table.score is not None else 0.0,
        pass_rate=table.pass_rate if table.pass_rate is not None else 0.0,
        results_json=json.dumps(table.to_dict(), default=str),
    )
    db.add(run)
    # Flush the parent row before its children: SQLite enforces the foreign key,
    # and SQLAlchemy would otherwise batch both inserts into one statement.
    await db.flush()

    for row in table.rows:
        if row.is_inconclusive:
            db.add(
                EvalResult(
                    id=str(uuid4()),
                    run_id=run.id,
                    case_id=row.case_id,
                    score=0.0,
                    passed=0,
                    actual_output="",
                    reasoning=_truncate(
                        json.dumps({"verdict": Verdict.INCONCLUSIVE.value, "reason": row.reason}, default=str),
                        4000,
                    ),
                    scoring_method=METHOD_INCONCLUSIVE,
                    duration_ms=row.duration_ms,
                )
            )
            continue
        db.add(
            EvalResult(
                id=str(uuid4()),
                run_id=run.id,
                case_id=row.case_id,
                score=float(row.score if row.score is not None else 0.0),
                passed=1 if row.verdict is Verdict.PASSED else 0,
                actual_output=json.dumps(row.detail, default=str)[:4000],
                reasoning=_truncate(
                    json.dumps({"verdict": row.verdict.value, "reason": row.reason}, default=str),
                    4000,
                ),
                scoring_method=_clamp_method(row.scoring_method or METHOD_ARCBENCH),
                duration_ms=row.duration_ms,
            )
        )

    await db.commit()
    await db.refresh(run)
    return run


async def load_stored_result(db: AsyncSession, run_id: str) -> TargetRunResult:
    """Rebuild a :class:`TargetRunResult` from a stored run.

    Rehydration goes through the table dict rather than the numeric columns, so
    an unmeasured run comes back as unmeasured instead of as a run that scored
    zero.
    """
    run = await db.get(EvalRun, run_id)
    if run is None:
        raise EvaluationError(f"evaluation run not found: {run_id}")
    stored = _load_json(run.results_json)
    if not isinstance(stored, dict):
        raise EvaluationError(f"evaluation run {run_id} has no readable score table")

    from app.eval.types import CaseRow, Evidence  # local import avoids a cycle

    evidence = Evidence.from_mapping(stored.get("evidence"))
    rows = [row for row in (CaseRow.from_mapping(r) for r in stored.get("rows") or []) if row is not None]
    verdicts = {row.case_id: row.verdict for row in rows}
    reasons = {row.case_id: row.reason for row in rows if row.reason}
    scored = any(row.verdict.is_scored for row in rows)
    status = str(stored.get("status") or "")
    return TargetRunResult(
        target=str(stored.get("target") or evidence.target or "unknown"),
        verdicts=verdicts,
        reasons=reasons,
        scored=scored,
        inconclusive=status == "inconclusive" or not scored,
        message=str(stored.get("message") or ""),
        evidence=evidence.to_dict(),
        capabilities=evidence.preflight,
    )


async def load_score_table(db: AsyncSession, run_id: str) -> ScoreTable:
    """Re-read a stored run as an honest :class:`ScoreTable`."""
    result = await load_stored_result(db, run_id)
    return score_table_from_stored(run_id, result)


async def list_runs_for_agent(db: AsyncSession, agent_id: str, limit: int = 20) -> list[EvalRun]:
    stmt = (
        select(EvalRun)
        .where(EvalRun.agent_id == agent_id)
        .order_by(EvalRun.created_at.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


def dataset_case_count(stored: Any) -> int:
    """Number of cases a stored score table claims to cover."""
    if not isinstance(stored, dict):
        return 0
    rows = stored.get("rows")
    return len(rows) if isinstance(rows, list) else 0


def stored_fingerprint(stored: Any) -> str:
    if not isinstance(stored, dict):
        return ""
    evidence = stored.get("evidence")
    if isinstance(evidence, dict):
        return str(evidence.get("fingerprint") or "")
    return fingerprint_for(str(stored.get("target") or "unknown"), {})

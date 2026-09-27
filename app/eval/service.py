"""The evaluation service: execute a target, score it, persist it, read it back."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

# Importing the built-in target module is what registers it. Additional targets
# register themselves the same way when this package is extended.
from app.eval import targets_arcbench as _builtin_targets  # noqa: F401  (registration side effect)
from app.eval.errors import EvaluationError
from app.eval.persistence import (
    ensure_dataset,
    load_score_table,
    persist_score_table,
)
from app.eval.scoring import build_score_table, fingerprint_for
from app.eval.targets import EvalTarget, TargetSpec, describe_targets, get_target
from app.eval.types import ScoreTable, TargetRunResult

RUNS_DIRNAME = "runs"


@dataclass(frozen=True)
class RunRequest:
    """A request to evaluate something.

    ``workdir`` is where the run's artifacts land. It must stay under
    ``app/eval/runs`` so a caller cannot point the adapter at an arbitrary
    directory.
    """

    target: str
    spec: dict[str, Any]
    config: dict[str, Any]
    agent_id: str
    user_id: str
    dataset_id: str = ""
    expected_cases: int = 0
    workdir: str = ""


class EvaluationService:
    """Runs registered evaluation targets and records their score tables.

    The service owns the sequence (execute, score, persist, return) and nothing
    else. All measurement decisions belong to the target, and all verdict
    decisions belong to :mod:`app.eval.scoring`.
    """

    def __init__(self, runs_root: Path | None = None) -> None:
        self.runs_root = Path(runs_root) if runs_root else Path(__file__).resolve().parent / RUNS_DIRNAME

    # ------------------------------------------------------------------ api

    def describe_targets(self) -> list[dict[str, str]]:
        return describe_targets()

    def get_target(self, name: str) -> EvalTarget:
        return get_target(name)

    def preflight(self, request: RunRequest) -> list[dict[str, Any]]:
        """Report what the target can measure, without running anything."""
        target = get_target(request.target)
        spec = self.build_spec(target, request)
        return [check.to_dict() for check in target.preflight(spec)]

    async def run(self, db: AsyncSession, request: RunRequest) -> ScoreTable:
        """Execute ``request`` end to end and persist the resulting score table."""
        target = get_target(request.target)
        spec = self.build_spec(target, request)

        result: TargetRunResult = target.execute(spec)
        fingerprint = fingerprint_for(request.target, result.evidence.get("inputs") or {})
        table = build_score_table(result, fingerprint=fingerprint, workdir=spec.workdir)

        dataset_id = request.dataset_id
        if not dataset_id:
            dataset = await self._ensure_dataset(db, request, target, spec, result)
            dataset_id = dataset.id
        run = await persist_score_table(
            db,
            table=table,
            user_id=request.user_id,
            dataset_id=dataset_id,
            agent_id=request.agent_id,
        )
        # Re-read through the same reduction the reader uses, so the returned
        # table is the one a subsequent GET will produce.
        reloaded = await load_score_table(db, run.id)
        return reloaded

    async def get(self, db: AsyncSession, run_id: str) -> ScoreTable:
        """Re-read a stored run as a score table."""
        return await load_score_table(db, run_id)

    async def _ensure_dataset(
        self,
        db: AsyncSession,
        request: RunRequest,
        target: EvalTarget,
        spec: TargetSpec,
        result: TargetRunResult,
    ) -> Any:
        """Create the dataset row describing what this run measured."""
        plan = target.build(spec)
        description = (
            f"target={request.target} workdir={spec.workdir} "
            f"fingerprint={fingerprint_for(request.target, result.evidence.get('inputs') or {})}"
        )
        return await ensure_dataset(
            db,
            user_id=request.user_id,
            name=f"{request.target} run inputs",
            description=description,
            case_count=len(result.verdicts),
            data=_case_data(plan, result),
        )

    # ------------------------------------------------------------- internals

    def build_spec(self, target: EvalTarget, request: RunRequest) -> TargetSpec:
        """Materialise a :class:`TargetSpec` with a validated workdir."""
        workdir = self.resolve_workdir(request, target)
        return TargetSpec(
            target=target.name,
            spec=dict(request.spec),
            config=dict(request.config),
            expected_cases=request.expected_cases,
            workdir=str(workdir),
        )

    def resolve_workdir(self, request: RunRequest, target: EvalTarget) -> Path:
        """Pick a run directory under ``app/eval/runs`` and create it."""
        supplied = str(request.workdir or "").strip()
        candidate = (
            Path(supplied).expanduser().resolve()
            if supplied
            else (self.runs_root / target.name).resolve()
        )
        allowed_root = self.runs_root.resolve()
        if not candidate.is_relative_to(allowed_root):
            raise EvaluationError(
                f"workdir must live under {allowed_root}; refusing to use {candidate}"
            )
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate


def _case_data(plan: dict[str, Any], result: TargetRunResult) -> list[Any]:
    """Case definitions stored on the dataset: the target's real inputs."""
    node_ids = sorted(result.verdicts)
    return [
        {
            "case_id": node_id,
            "deliverable_dir": str(plan.get("deliverable", "")),
            "tests_dir": str(plan.get("tests_dir", "")),
            "web_port": plan.get("web_port"),
        }
        for node_id in node_ids
    ]


def summary_json(table: ScoreTable) -> str:
    """Compact one-line JSON for logs and CLI output."""
    return json.dumps(
        {
            "run_id": table.run_id,
            "target": table.target,
            "status": table.status.value,
            "scored": f"{table.scored_cases}/{table.total_cases}",
            "score": table.score,
            "pass_rate": table.pass_rate,
        },
        default=str,
    )

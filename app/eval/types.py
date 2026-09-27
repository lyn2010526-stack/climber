"""Result types for the evaluation runtime, and the invariants they enforce.

The central invariant of this module is stated once here and enforced
structurally in :meth:`CaseRow.__post_init__` and
:meth:`ScoreTable.__post_init__`:

    A score exists if and only if a real measurement produced it.

Concretely, a :class:`CaseRow` whose verdict is
:data:`Verdict.INCONCLUSIVE` cannot carry a score at all, and a
:class:`ScoreTable` whose run was inconclusive reports ``None`` for its
aggregate score and pass rate rather than a number that would be mistaken for a
measurement.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

PASSED = "passed"
FAILED = "failed"
INCONCLUSIVE = "inconclusive"


class Verdict(StrEnum):
    """Outcome of evaluating a single case.

    ``INCONCLUSIVE`` is a first-class outcome, not an error and not a failure.
    It means the evaluation could not be performed honestly: the infrastructure
    was unavailable, the report was missing or unreadable, or no evidence
    covered this case.
    """

    PASSED = PASSED
    FAILED = FAILED
    INCONCLUSIVE = INCONCLUSIVE

    @property
    def is_scored(self) -> bool:
        """True when the verdict was derived from a real measurement."""
        return self in (Verdict.PASSED, Verdict.FAILED)


class RunStatus(StrEnum):
    """Outcome of an evaluation run as a whole."""

    MEASURED = "measured"
    INCONCLUSIVE = "inconclusive"


class CapabilityState(StrEnum):
    """Result of a single preflight capability check."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CapabilityCheck:
    """A preflight probe of one thing a target needs in order to measure.

    ``required=False`` marks a capability that degrades evidence quality without
    blocking the run. ``UNKNOWN`` means the probe itself could not complete; the
    runtime never turns an unknown into an available.
    """

    name: str
    state: CapabilityState
    detail: str = ""
    required: bool = True

    @property
    def blocking(self) -> bool:
        """True when this capability prevents an honest measurement."""
        return self.required and self.state is not CapabilityState.AVAILABLE

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "detail": self.detail,
            "required": self.required,
        }

    @classmethod
    def from_mapping(cls, raw: Any) -> CapabilityCheck | None:
        if not isinstance(raw, dict):
            return None
        name = str(raw.get("name") or "").strip()
        if not name:
            return None
        try:
            state = CapabilityState(str(raw.get("state") or "").strip() or CapabilityState.UNKNOWN.value)
        except ValueError:
            state = CapabilityState.UNKNOWN
        return cls(
            name=name,
            state=state,
            detail=str(raw.get("detail") or ""),
            required=bool(raw.get("required", True)),
        )


def capability_from_mapping(raw: Any) -> list[CapabilityCheck]:
    """Rebuild a capability list from stored JSON, tolerating junk entries."""
    if not isinstance(raw, list):
        return []
    checks = [CapabilityCheck.from_mapping(item) for item in raw]
    return [check for check in checks if check is not None]


@dataclass(frozen=True)
class CaseRow:
    """One row of the score table: a single evaluated case.

    A passed case scores ``1.0`` and a failed case scores ``0.0``. Those are
    derived from the target's own boolean verdict, which is a measurement, not a
    default. An inconclusive case has no score at all.
    """

    case_id: str
    verdict: Verdict
    score: float | None = None
    reason: str = ""
    scoring_method: str = ""
    duration_ms: float = 0.0
    detail: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.case_id or "").strip():
            raise ValueError("case_id is required")
        if self.verdict.is_scored and self.score is None:
            raise ValueError(f"case {self.case_id!r} is {self.verdict.value} but carries no score")
        if not self.verdict.is_scored and self.score is not None:
            raise ValueError(
                f"case {self.case_id!r} is {self.verdict.value} and must not carry a score; "
                "a fabricated number is worse than no number"
            )
        if self.score is not None and not math.isfinite(self.score):
            raise ValueError(f"case {self.case_id!r} has a non-finite score")

    @property
    def is_inconclusive(self) -> bool:
        return self.verdict is Verdict.INCONCLUSIVE

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "verdict": self.verdict.value,
            "score": self.score,
            "reason": self.reason,
            "scoring_method": self.scoring_method,
            "duration_ms": round(float(self.duration_ms), 3),
            "detail": dict(self.detail),
        }

    @classmethod
    def from_mapping(cls, raw: Any) -> CaseRow | None:
        if not isinstance(raw, dict):
            return None
        case_id = str(raw.get("case_id") or "").strip()
        if not case_id:
            return None
        try:
            verdict = Verdict(str(raw.get("verdict") or "").strip() or INCONCLUSIVE)
        except ValueError:
            verdict = Verdict.INCONCLUSIVE
        score = raw.get("score")
        if not verdict.is_scored or not isinstance(score, int | float) or isinstance(score, bool):
            score = None
        detail = raw.get("detail")
        return cls(
            case_id=case_id,
            verdict=verdict,
            score=float(score) if score is not None else None,
            reason=str(raw.get("reason") or ""),
            scoring_method=str(raw.get("scoring_method") or ""),
            duration_ms=float(raw.get("duration_ms") or 0.0),
            detail=dict(detail) if isinstance(detail, dict) else {},
        )


@dataclass(frozen=True)
class TargetRunResult:
    """What a target reports back from one execution.

    A target must fill ``verdicts`` and ``reasons`` consistently: any case it
    cannot measure appears in ``reasons`` with a real cause. ``evidence`` holds
    the artifact the score table is later recomputed from, which is what makes a
    stored run reproducible without re-executing it.
    """

    target: str
    verdicts: dict[str, Verdict] = field(default_factory=dict)
    reasons: dict[str, str] = field(default_factory=dict)
    scored: bool = False
    inconclusive: bool = False
    message: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    capabilities: list[CapabilityCheck] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "verdicts": {key: value.value for key, value in self.verdicts.items()},
            "reasons": dict(self.reasons),
            "scored": self.scored,
            "inconclusive": self.inconclusive,
            "message": self.message,
            "evidence": dict(self.evidence),
            "capabilities": [check.to_dict() for check in self.capabilities],
            "duration_ms": round(float(self.duration_ms), 3),
        }

    @classmethod
    def from_mapping(cls, raw: Any) -> TargetRunResult:
        if not isinstance(raw, dict):
            return cls(target="unknown", message="target produced no evidence")
        raw_verdicts = raw.get("verdicts")
        verdicts: dict[str, Verdict] = {}
        if isinstance(raw_verdicts, dict):
            for key, value in raw_verdicts.items():
                try:
                    verdicts[str(key)] = Verdict(str(value))
                except ValueError:
                    verdicts[str(key)] = Verdict.INCONCLUSIVE
        raw_reasons = raw.get("reasons")
        reasons = {str(k): str(v) for k, v in raw_reasons.items()} if isinstance(raw_reasons, dict) else {}
        evidence = raw.get("evidence")
        return cls(
            target=str(raw.get("target") or "unknown"),
            verdicts=verdicts,
            reasons=reasons,
            scored=bool(raw.get("scored")),
            inconclusive=bool(raw.get("inconclusive")),
            message=str(raw.get("message") or ""),
            evidence=dict(evidence) if isinstance(evidence, dict) else {},
            capabilities=capability_from_mapping(raw.get("capabilities")),
            duration_ms=float(raw.get("duration_ms") or 0.0),
        )


def run_result_from_mapping(raw: Any) -> TargetRunResult:
    """Module-level alias kept explicit for callers that rehydrate stored runs."""
    return TargetRunResult.from_mapping(raw)


@dataclass(frozen=True)
class Evidence:
    """The reproduction record of a run.

    ``fingerprint`` is a stable digest of the inputs that decide the outcome
    (target identity, spec digests, tool digests, requirement digest), so two
    runs of the same inputs are recognisable as comparable. ``preflight`` is the
    capability snapshot, kept separately from the acceptance summary because it
    describes what *could* be measured, while the summary describes what *was*.
    """

    fingerprint: str
    target: str
    inputs: dict[str, Any] = field(default_factory=dict)
    preflight: list[CapabilityCheck] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    arc_events: list[dict[str, Any]] = field(default_factory=list)
    workdir: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "fingerprint": self.fingerprint,
            "target": self.target,
            "inputs": dict(self.inputs),
            "preflight": [check.to_dict() for check in self.preflight],
            "summary": dict(self.summary),
            "arc_events": [dict(event) for event in self.arc_events],
            "workdir": self.workdir,
        }

    @classmethod
    def from_mapping(cls, raw: Any) -> Evidence:
        if not isinstance(raw, dict):
            return cls(fingerprint="", target="unknown")
        summary = raw.get("summary")
        inputs = raw.get("inputs")
        arc_events = raw.get("arc_events")
        return cls(
            fingerprint=str(raw.get("fingerprint") or ""),
            target=str(raw.get("target") or "unknown"),
            inputs=dict(inputs) if isinstance(inputs, dict) else {},
            preflight=capability_from_mapping(raw.get("preflight")),
            summary=dict(summary) if isinstance(summary, dict) else {},
            arc_events=[dict(e) for e in arc_events if isinstance(e, dict)]
            if isinstance(arc_events, list)
            else [],
            workdir=str(raw.get("workdir") or ""),
        )


@dataclass(frozen=True)
class ScoreTable:
    """The reproducible score table produced by one run.

    ``score`` and ``pass_rate`` are ``None`` whenever the run produced no usable
    measurement, and ``pass_rate`` is additionally ``None`` when no case was
    scored. ``coverage`` is the fraction of cases backed by evidence, which is
    what distinguishes "scored 0.0" from "measured nothing".
    """

    run_id: str
    target: str
    status: RunStatus
    rows: list[CaseRow] = field(default_factory=list)
    inconclusive_reasons: list[str] = field(default_factory=list)
    evidence: Evidence = field(default_factory=lambda: Evidence(fingerprint="", target="unknown"))
    message: str = ""

    @property
    def total_cases(self) -> int:
        return len(self.rows)

    @property
    def scored_cases(self) -> int:
        return sum(1 for row in self.rows if row.verdict.is_scored)

    @property
    def passed_cases(self) -> int:
        return sum(1 for row in self.rows if row.verdict is Verdict.PASSED)

    @property
    def failed_cases(self) -> int:
        return sum(1 for row in self.rows if row.verdict is Verdict.FAILED)

    @property
    def inconclusive_cases(self) -> int:
        return sum(1 for row in self.rows if row.is_inconclusive)

    @property
    def score(self) -> float | None:
        """Mean score over scored cases, or ``None`` when nothing was scored."""
        scores = [row.score for row in self.rows if row.score is not None]
        if not scores:
            return None
        return round(sum(scores) / len(scores), 6)

    @property
    def pass_rate(self) -> float | None:
        """Passed share of scored cases, or ``None`` when nothing was scored.

        Deliberately ``None`` rather than ``0.0`` for an unmeasured run: a zero
        pass rate claims every case was measured and failed.
        """
        scored = self.scored_cases
        if scored == 0:
            return None
        return round(self.passed_cases / scored, 6)

    @property
    def coverage(self) -> float:
        """Fraction of cases backed by evidence."""
        if not self.rows:
            return 0.0
        return round(self.scored_cases / len(self.rows), 6)

    @property
    def is_inconclusive(self) -> bool:
        return self.status is RunStatus.INCONCLUSIVE

    def row_for(self, case_id: str) -> CaseRow | None:
        for row in self.rows:
            if row.case_id == case_id:
                return row
        return None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "run_id": self.run_id,
            "target": self.target,
            "status": self.status.value,
            "message": self.message,
            "total_cases": self.total_cases,
            "scored_cases": self.scored_cases,
            "passed_cases": self.passed_cases,
            "failed_cases": self.failed_cases,
            "inconclusive_cases": self.inconclusive_cases,
            "score": self.score,
            "pass_rate": self.pass_rate,
            "coverage": self.coverage,
            "inconclusive_reasons": list(self.inconclusive_reasons),
            "capabilities": [check.to_dict() for check in self.evidence.preflight],
            "fingerprint": self.evidence.fingerprint,
            "rows": [row.to_dict() for row in self.rows],
        }
        if self.evidence.workdir:
            # The full evidence block is stored so a re-read can reproduce the
            # table from the artifact rather than from cached numbers. It is
            # dropped from responses by the API layer, not from storage.
            payload["evidence"] = self.evidence.to_dict()
        return payload


def target_run_result_from_mapping(raw: Any) -> TargetRunResult:
    """Public rehydration helper for stored target results."""
    return TargetRunResult.from_mapping(raw)

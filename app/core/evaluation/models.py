"""Core evaluation data models: scenarios, trajectories, verdicts, reports."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class RubricItem:
    """One rubric criterion with weight, essentiality and judging hint.

    Deterministic judging uses substring sets: the transcript must contain
    at least one ``contains_any`` entry (case-insensitive) and none of the
    ``not_contains_any`` entries. An item with neither set needs a semantic
    judge; deterministic judging fails closed without checkable evidence.
    """

    item_id: str
    description: str
    contains_any: list[str] = field(default_factory=list)
    not_contains_any: list[str] = field(default_factory=list)
    weight: float = 1.0
    # Essential items failing -> whole case fails (veto semantics).
    essential: bool = False
    # Veto items failing -> hard fail regardless of score.
    veto: bool = False

    def __post_init__(self) -> None:
        if not math.isfinite(self.weight) or self.weight <= 0:
            raise ValueError("rubric weight must be finite and positive")


@dataclass
class EvalScenario:
    """One evaluation case: user input, expected key points and a rubric.

    Answers follow the "acceptable behavior set" convention: expected
    points are hints for judging, not exact-match strings.
    """

    name: str
    user_input: str
    expected_points: list[str] = field(default_factory=list)
    rubric: list[RubricItem] = field(default_factory=list)
    scenario_id: str = field(default_factory=lambda: str(uuid4()))
    difficulty: str = "normal"  # easy | normal | hard
    canary: str | None = None  # leakage marker copied into trajectory meta
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvalScenario:
        rubric = [RubricItem(**item) for item in data.get("rubric", [])]
        return cls(
            scenario_id=data.get("scenario_id") or str(uuid4()),
            name=data["name"],
            user_input=data["user_input"],
            expected_points=data.get("expected_points", []),
            rubric=rubric,
            difficulty=data.get("difficulty", "normal"),
            canary=data.get("canary"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class CallRecord:
    """One step inside a trajectory: an LLM call or a tool call."""

    step: int
    kind: str  # "llm" | "tool"
    name: str = ""  # tool name (kind=tool) or model id (kind=llm)
    arguments: dict[str, Any] = field(default_factory=dict)
    output: str = ""
    tokens_used: int = 0


@dataclass
class Trajectory:
    """Everything an agent run produced, captured for judging."""

    scenario_id: str
    user_input: str
    output: str = ""
    calls: list[CallRecord] = field(default_factory=list)
    tokens_used: int = 0
    status: str = "completed"  # completed | failed | error
    error: str | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_call(self, record: CallRecord) -> None:
        self.calls.append(record)


@dataclass
class ItemVerdict:
    """Judge outcome for one rubric item."""

    item_id: str
    passed: bool
    reason: str = ""
    weight: float = 1.0
    essential: bool = False
    veto: bool = False


@dataclass
class EvaluationResult:
    """Scored outcome of one trajectory against one rubric."""

    scenario_id: str
    score: float  # 0.0-1.0
    passed: bool
    verdicts: list[ItemVerdict] = field(default_factory=list)
    failure_reasons: list[str] = field(default_factory=list)
    judge: str = "deterministic"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScenarioReport:
    """Aggregated result for one scenario, possibly with k candidates."""

    scenario_id: str
    scenario_name: str
    results: list[EvaluationResult] = field(default_factory=list)
    best_score: float = 0.0
    mean_score: float = 0.0
    pass_count: int = 0  # candidates that fully passed
    passed: bool = False  # best candidate passed (pass@1 = any-pass)
    trajectories: list[Trajectory] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "best_score": self.best_score,
            "mean_score": self.mean_score,
            "pass_count": self.pass_count,
            "passed": self.passed,
            "results": [r.to_dict() for r in self.results],
            "trajectories": [asdict(t) for t in self.trajectories],
        }


@dataclass
class EvaluationReport:
    """Full report of one evaluation run over a scenario set."""

    report_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=_utcnow_iso)
    scenarios: list[ScenarioReport] = field(default_factory=list)
    total_scenarios: int = 0
    passed_scenarios: int = 0
    average_score: float = 0.0
    pass_at_k: dict[str, Any] = field(default_factory=dict)
    pass_hat_k: dict[str, Any] = field(default_factory=dict)
    total_tokens: int = 0
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "created_at": self.created_at,
            "total_scenarios": self.total_scenarios,
            "passed_scenarios": self.passed_scenarios,
            "average_score": self.average_score,
            "pass_at_k": self.pass_at_k,
            "pass_hat_k": self.pass_hat_k,
            "total_tokens": self.total_tokens,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
            "scenarios": [s.to_dict() for s in self.scenarios],
        }

    def to_baseline(self) -> dict[str, Any]:
        """Compact baseline snapshot: per-scenario best score only."""
        return {
            "report_id": self.report_id,
            "created_at": self.created_at,
            "scores": {s.scenario_id: s.best_score for s in self.scenarios},
            "average_score": self.average_score,
            "passes": {s.scenario_id: s.passed for s in self.scenarios},
        }

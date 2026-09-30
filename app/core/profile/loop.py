"""A small, local-only profile learning loop for Agent interaction events.

The implementation is deliberately statistical. It provides useful, inspectable
signals for a future profile adapter without claiming neural-network inference.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal


class PrivacyBoundaryError(ValueError):
    """Raised when an event is outside the Agent-internal input boundary."""


Outcome = Literal["success", "failure"]
Feedback = Literal["positive", "negative", "neutral"]


@dataclass(frozen=True, slots=True)
class ProfileEvent:
    """An interaction signal accepted by the local profile loop.

    ``source`` is intentionally constrained to Agent-internal event producers.
    The service never fetches or infers data from external user data systems.
    """

    instruction: str
    task_type: str
    outcome: Outcome
    interrupted: bool = False
    retried: bool = False
    reasoning_level: str = "standard"
    tool: str | None = None
    feedback: Feedback = "neutral"
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    source: str = "agent_internal"


@dataclass(frozen=True, slots=True)
class ProfileSummary:
    """Low-dimensional, advisory profile projection with audit metadata."""

    task_preferences: dict[str, float]
    tool_preferences: dict[str, float]
    reasoning_preferences: dict[str, float]
    retry_rate: float
    interruption_rate: float
    success_rate: float
    confidence: float
    provenance: tuple[str, ...]
    enabled: bool


@dataclass
class _FeatureStats:
    weight: float = 0.0
    positive: float = 0.0
    negative: float = 0.0

    def add(self, weight: float, signal: float) -> None:
        self.weight += weight
        if signal > 0:
            self.positive += weight * signal
        elif signal < 0:
            self.negative += weight * -signal

    @property
    def calibration(self) -> float:
        total = self.positive + self.negative
        return 0.5 if total == 0 else self.positive / total


class ProfileLoopService:
    """Build an advisory profile from Agent-internal events in memory."""

    ALLOWED_SOURCES = frozenset({"agent_internal", "instruction_trace"})

    def __init__(self, *, enabled: bool = True, half_life_days: float = 30.0) -> None:
        if half_life_days <= 0:
            raise ValueError("half_life_days must be positive")
        self.enabled = enabled
        self.half_life_days = half_life_days
        self._events: list[ProfileEvent] = []

    def record(self, event: ProfileEvent) -> bool:
        """Record one event after checking its privacy boundary."""
        self._validate_event(event)
        if not self.enabled:
            return False
        self._events.append(event)
        return True

    def summary(self, *, as_of: datetime | None = None) -> ProfileSummary:
        """Return normalized preferences and calibrated confidence."""
        if not self.enabled:
            return ProfileSummary({}, {}, {}, 0.0, 0.0, 0.0, 0.0, (), False)

        reference = _utc(as_of or datetime.now(UTC))
        task, tools, reasoning = {}, {}, {}
        total = success = retries = interruptions = 0.0
        for event in self._events:
            weight = self._weight(event, reference)
            signal = self._signal(event)
            total += weight
            success += weight * (1.0 if event.outcome == "success" else 0.0)
            retries += weight * (1.0 if event.retried else 0.0)
            interruptions += weight * (1.0 if event.interrupted else 0.0)
            _add_signal(task, event.task_type, weight, signal)
            _add_signal(reasoning, event.reasoning_level, weight, signal)
            if event.tool:
                _add_signal(tools, event.tool, weight, signal)

        sample_confidence = min(1.0, total / 5.0)
        return ProfileSummary(
            task_preferences=_normalize(task),
            tool_preferences=_normalize(tools),
            reasoning_preferences=_normalize(reasoning),
            retry_rate=_ratio(retries, total),
            interruption_rate=_ratio(interruptions, total),
            success_rate=_ratio(success, total),
            confidence=round(sample_confidence, 4),
            provenance=("agent_internal_event", "exponential_time_decay", "outcome_feedback_calibration"),
            enabled=True,
        )

    def auxiliary_context(
        self, current_instruction: str, *, as_of: datetime | None = None
    ) -> dict[str, object]:
        """Return profile hints while preserving the current instruction as authority."""
        summary = self.summary(as_of=as_of)
        return {
            "current_instruction": current_instruction,
            "profile_role": "auxiliary_context",
            "profile_may_not_override_current_instruction": True,
            "suggestions": {
                "task_type": _top(summary.task_preferences),
                "tool": _top(summary.tool_preferences),
                "reasoning_level": _top(summary.reasoning_preferences),
            },
            "confidence": summary.confidence,
            "provenance": summary.provenance,
            "enabled": summary.enabled,
        }

    def _validate_event(self, event: ProfileEvent) -> None:
        if event.source not in self.ALLOWED_SOURCES:
            raise PrivacyBoundaryError(
                "profile loop accepts Agent-internal events only; external data sources are rejected"
            )
        if not event.instruction.strip() or not event.task_type.strip():
            raise ValueError("instruction and task_type are required")
        if event.outcome not in ("success", "failure"):
            raise ValueError("outcome must be success or failure")
        if event.feedback not in ("positive", "negative", "neutral"):
            raise ValueError("feedback must be positive, negative, or neutral")

    def _weight(self, event: ProfileEvent, reference: datetime) -> float:
        age_days = max(0.0, (reference - _utc(event.occurred_at)).total_seconds() / 86400)
        return math.exp(-math.log(2) * age_days / self.half_life_days)

    @staticmethod
    def _signal(event: ProfileEvent) -> float:
        outcome = 1.0 if event.outcome == "success" else -1.0
        feedback = {"positive": 0.35, "negative": -0.35, "neutral": 0.0}[event.feedback]
        return max(-1.0, min(1.0, outcome + feedback))


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _add_signal(target: dict[str, _FeatureStats], key: str, weight: float, signal: float) -> None:
    target.setdefault(key, _FeatureStats()).add(weight, signal)


def _normalize(values: dict[str, _FeatureStats]) -> dict[str, float]:
    """Blend prevalence with outcome calibration into a [0, 1] score.

    Prevalence alone would reward frequently-seen-but-always-failing task types,
    so the score is prevalence modulated by the outcome/feedback calibration,
    which maps a purely negative history to 0 and a purely positive one to 1.
    """
    if not values:
        return {}
    total_weight = sum(item.weight for item in values.values())
    return {
        key: round(
            (item.weight / total_weight) * (0.5 + 0.5 * item.calibration) * (2 * item.calibration),
            4,
        )
        for key, item in values.items()
    }


def _ratio(numerator: float, denominator: float) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _top(values: dict[str, float]) -> str | None:
    return max(values, key=values.get) if values else None

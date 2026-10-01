"""A small, local-only profile learning loop for Agent interaction events.

The implementation is deliberately statistical. It provides useful, inspectable
signals for a future profile adapter without claiming neural-network inference.

Algorithm inventory (see docs/DESIGN.md section 4.1, 用户画像层核心算法):

- Time-decay weighting (``ProfileLoopService._weight``): exponential half-life
  decay so recent behaviour always outweighs stale history.
- Weak-supervision calibration (``_FeatureStats.calibration``): task outcome
  and explicit feedback are the only labels; a feature's score is prevalence
  modulated by its success calibration, not raw frequency.
- Feature hashing embedding (``embed_event``): each categorical field is
  projected into a fixed-size dense vector via the hashing trick (Weinberger
  et al., 2009), so new task types/tools/reasoning levels never require a
  vocabulary migration.
- Incremental online clustering (``OnlineKMeans``): a single-pass, streaming
  k-means (MacQueen, 1967) that updates centroids as each event arrives with
  no stored history replay and no offline retraining step.
"""

from __future__ import annotations

import hashlib
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
    persona_cluster: int | None = None
    persona_cluster_confidence: float = 0.0


def embed_event(event: ProfileEvent, *, dim: int = 12) -> tuple[float, ...]:
    """Project an event's categorical features into a fixed-size dense vector.

    Uses the hashing trick (Weinberger et al., 2009): each ``field:value``
    pair is hashed into a bucket in ``[0, dim)`` with a deterministic signed
    contribution, then the vector is L2-normalized. New task types, tools, or
    reasoning levels are embedded immediately with no vocabulary table and no
    migration, which matches the single-pass, no-offline-retrain constraint
    this loop operates under.
    """
    vector = [0.0] * dim
    fields: list[tuple[str, str]] = [
        ("task_type", event.task_type),
        ("reasoning_level", event.reasoning_level),
        ("outcome", event.outcome),
        ("feedback", event.feedback),
    ]
    if event.tool:
        fields.append(("tool", event.tool))
    for field_name, value in fields:
        bucket, sign = _hash_bucket(f"{field_name}:{value}", dim)
        vector[bucket] += sign
    norm = math.sqrt(sum(component * component for component in vector))
    if norm > 0:
        vector = [component / norm for component in vector]
    return tuple(vector)


def _hash_bucket(token: str, dim: int) -> tuple[int, float]:
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:4], "big") % dim
    sign = 1.0 if digest[4] % 2 == 0 else -1.0
    return bucket, sign


def _squared_distance(a: tuple[float, ...], b: list[float]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b, strict=True))


class OnlineKMeans:
    """Single-pass streaming k-means (MacQueen, 1967).

    Every call assigns the incoming vector to its nearest centroid and nudges
    that centroid toward it with a running-mean learning rate
    (``weight / total_weight_of_cluster``). There is no stored event replay
    and no offline retraining step, so the private per-user instance keeps
    learning incrementally for as long as the process runs, with O(k) memory.
    """

    def __init__(self, *, k: int, dim: int) -> None:
        if k < 1:
            raise ValueError("k must be at least 1")
        if dim < 1:
            raise ValueError("dim must be at least 1")
        self.k = k
        self.dim = dim
        self._centroids: list[list[float]] = []
        self._weights: list[float] = []

    def partial_fit(self, vector: tuple[float, ...], *, weight: float = 1.0) -> tuple[int, float]:
        """Assign ``vector`` to a cluster and update that cluster's centroid.

        Returns ``(cluster_id, distance_to_centroid)``. The first ``k``
        distinct calls seed one centroid each (distance 0.0 by definition);
        every call after that performs the MacQueen update.
        """
        if len(vector) != self.dim:
            raise ValueError(f"expected a {self.dim}-dimensional vector, got {len(vector)}")
        if weight <= 0:
            raise ValueError("weight must be positive")
        if len(self._centroids) < self.k:
            self._centroids.append(list(vector))
            self._weights.append(weight)
            return len(self._centroids) - 1, 0.0

        cluster_id = min(range(self.k), key=lambda i: _squared_distance(vector, self._centroids[i]))
        distance = math.sqrt(_squared_distance(vector, self._centroids[cluster_id]))
        self._weights[cluster_id] += weight
        rate = weight / self._weights[cluster_id]
        centroid = self._centroids[cluster_id]
        for i, value in enumerate(vector):
            centroid[i] += rate * (value - centroid[i])
        return cluster_id, distance

    @property
    def cluster_weights(self) -> tuple[float, ...]:
        """Total assigned weight per cluster, for inspection and the summary."""
        return tuple(self._weights)

    @property
    def is_seeded(self) -> bool:
        return len(self._centroids) >= self.k


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
    EMBEDDING_DIM = 12

    def __init__(
        self,
        *,
        enabled: bool = True,
        half_life_days: float = 30.0,
        persona_clusters: int = 4,
    ) -> None:
        if half_life_days <= 0:
            raise ValueError("half_life_days must be positive")
        if persona_clusters < 1:
            raise ValueError("persona_clusters must be at least 1")
        self.enabled = enabled
        self.half_life_days = half_life_days
        self._events: list[ProfileEvent] = []
        # Incremental online clustering: updated one event at a time, never
        # replayed or retrained from history, so this stays O(k) regardless
        # of how many events this private instance has ever seen.
        self._cluster_model = OnlineKMeans(k=persona_clusters, dim=self.EMBEDDING_DIM)
        self._last_cluster: tuple[int, float] | None = None

    def record(self, event: ProfileEvent) -> bool:
        """Record one event after checking its privacy boundary."""
        self._validate_event(event)
        if not self.enabled:
            return False
        self._events.append(event)
        weight = self._weight(event, datetime.now(UTC))
        vector = embed_event(event, dim=self.EMBEDDING_DIM)
        self._last_cluster = self._cluster_model.partial_fit(vector, weight=max(weight, 1e-6))
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
            provenance=(
                "agent_internal_event",
                "exponential_time_decay",
                "outcome_feedback_calibration",
                "hashing_trick_embedding",
                "online_kmeans_clustering",
            ),
            enabled=True,
            persona_cluster=self._persona_cluster_id(),
            persona_cluster_confidence=self._persona_cluster_confidence(),
        )

    def _persona_cluster_id(self) -> int | None:
        return self._last_cluster[0] if self._last_cluster is not None else None

    def _persona_cluster_confidence(self) -> float:
        """Share of total clustering weight held by the most recently assigned cluster.

        A low value means the private per-user cluster model has not yet seen
        enough events to separate a stable persona from the rest; it rises as
        one cluster accumulates a dominant share of the weighted event stream.
        """
        if self._last_cluster is None:
            return 0.0
        weights = self._cluster_model.cluster_weights
        total_weight = sum(weights)
        if total_weight <= 0:
            return 0.0
        cluster_id, _distance = self._last_cluster
        return round(weights[cluster_id] / total_weight, 4)

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

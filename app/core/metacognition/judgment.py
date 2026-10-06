"""Judgment layer — calibrated confidence, continuous goal scoring, dissent aggregation.

A deterministic, local-only decision layer that keeps judgment outputs honest:

- Confidence is calibrated against evidence and contradictions and clamped
  away from 0/1 extremes, so low-confidence conclusions are visibly downgraded
  instead of passing as certain ("anti-overclaiming").
- Goal attainment is scored on a continuous [0, 1] scale via a weighted
  geometric mean, so a weak sub-signal drags the result down instead of being
  averaged away into a binary success/fail call.
- Aggregating multiple sources preserves minority opinions and flags when a
  single high-confidence source dominates the verdict ("emergence guard").

The module performs zero I/O and zero LLM calls; every function is a pure
function of its inputs and fully reproducible.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

_CONFIDENCE_FLOOR = 0.05
_CONFIDENCE_CEILING = 0.95
_EVIDENCE_SATURATION = 10.0
_CONTRADICTION_DECAY = 0.6
_VERDICT_GAP = 0.3
_FP_TOLERANCE = 1e-9


def _finite(value: float, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


@dataclass(frozen=True, slots=True)
class Judgment:
    """One judgment claim with its meta-cognitive assessment context.

    ``confidence`` is the self-reported certainty in [0, 1]; ``scale`` is the
    continuous goal-attainment degree in [0, 1] (never a boolean verdict);
    ``dissent`` holds minority opinions that survived aggregation; ``sources``
    counts the inputs the claim was drawn from.
    """

    claim: str
    confidence: float
    scale: float
    dissent: tuple[str, ...] = ()
    sources: int = 0

    def __post_init__(self) -> None:
        if not math.isfinite(self.confidence) or not math.isfinite(self.scale):
            raise ValueError("confidence and scale must be finite")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be within [0, 1]")
        if not 0.0 <= self.scale <= 1.0:
            raise ValueError("scale must be within [0, 1]")
        if self.sources < 0:
            raise ValueError("sources must be non-negative")

    def to_dict(self) -> dict[str, object]:
        return {
            "claim": self.claim,
            "confidence": self.confidence,
            "scale": self.scale,
            "dissent": list(self.dissent),
            "sources": self.sources,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> Judgment:
        dissent = payload.get("dissent") or []
        return cls(
            claim=str(payload["claim"]),
            confidence=float(payload["confidence"]),
            scale=float(payload["scale"]),
            dissent=tuple(str(item) for item in dissent),
            sources=int(payload.get("sources") or 0),
        )


def calibrate(
    raw_confidence: float,
    *,
    evidence_count: int,
    contradiction_count: int = 0,
) -> float:
    """Confidence-weighted counterbalance: evidence lifts, contradictions sink.

    Evidence pushes the raw confidence toward the ceiling with logarithmic
    saturation; each contradiction applies a multiplicative decay. The result
    is clamped to [0.05, 0.95] so no judgment can ever report absolute
    certainty or absolute impossibility.
    """
    base = min(max(_finite(raw_confidence, "raw_confidence"), 0.0), 1.0)
    evidence = max(int(evidence_count), 0)
    contradictions = max(int(contradiction_count), 0)

    evidence_log = math.log1p(evidence)
    saturation_log = math.log1p(_EVIDENCE_SATURATION)
    boosted = base + (_CONFIDENCE_CEILING - base) * (evidence_log / (evidence_log + saturation_log))
    decayed = boosted * (_CONTRADICTION_DECAY**contradictions)
    return min(max(decayed, _CONFIDENCE_FLOOR), _CONFIDENCE_CEILING)


def continuous_goal(
    progress_signals: Sequence[float | None],
    *,
    weights: Sequence[float] | None = None,
) -> float:
    """Non-boolean goal discrimination on a continuous [0, 1] scale.

    Returns the weighted geometric mean of the progress signals. A geometric
    mean punishes weak sub-signals harder than an arithmetic mean, so a single
    failing dimension drags attainment down instead of hiding behind stronger
    ones. Any missing (``None``) or non-positive signal yields 0.0.
    """
    signals = [
        0.0 if signal is None else min(max(_finite(signal, "progress signal"), 0.0), 1.0)
        for signal in progress_signals
    ]
    if not signals:
        return 0.0

    if weights is None:
        weight_values = [1.0] * len(signals)
    else:
        weight_values = [_finite(weight, "weight") for weight in weights]
        if len(weight_values) != len(signals):
            raise ValueError("weights must match progress_signals in length")
        if any(weight < 0.0 for weight in weight_values):
            raise ValueError("weights must be non-negative")
        if all(weight == 0.0 for weight in weight_values):
            raise ValueError("weights must not sum to zero")

    included = [
        (signal, weight)
        for signal, weight in zip(signals, weight_values, strict=True)
        if weight > 0.0
    ]
    if any(signal <= 0.0 for signal, _ in included):
        return 0.0

    total_weight = sum(weight for _, weight in included)
    log_score = sum(weight * math.log(signal) for signal, weight in included)
    return min(max(math.exp(log_score / total_weight), 0.0), 1.0)


def aggregate_dissent(
    judgments: Sequence[Judgment],
    *,
    dominance_cap: float = 0.85,
) -> tuple[Judgment, bool]:
    """Emergence guard: aggregate judgments while keeping minority voices visible.

    Each judgment is weighted by its normalized confidence. When the highest
    share exceeds ``dominance_cap`` the verdict is flagged as dominated by a
    single strong signal. The aggregated judgment carries the leading claim
    and keeps the most-voted minority opinion from all ``dissent`` tuples so
    disagreement stays visible outside the majority call.
    """
    if not judgments:
        raise ValueError("judgments must not be empty")
    if not 0.0 < dominance_cap <= 1.0:
        raise ValueError("dominance_cap must be within (0, 1]")

    total_confidence = sum(judgment.confidence for judgment in judgments)
    if total_confidence > 0.0:
        share_weights = [judgment.confidence / total_confidence for judgment in judgments]
    else:
        share_weights = [1.0 / len(judgments)] * len(judgments)

    top_index = max(range(len(judgments)), key=lambda i: share_weights[i])
    top = judgments[top_index]
    dominated = (share_weights[top_index] - dominance_cap) > _FP_TOLERANCE

    dissent_counts: Counter[str] = Counter()
    for judgment in judgments:
        dissent_counts.update(judgment.dissent)
    top_dissent = dissent_counts.most_common(1)
    kept_dissent = tuple(dissent for dissent, _ in top_dissent)

    aggregated = Judgment(
        claim=top.claim,
        confidence=sum(
            weight * judgment.confidence
            for weight, judgment in zip(share_weights, judgments, strict=True)
        ),
        scale=sum(
            weight * judgment.scale
            for weight, judgment in zip(share_weights, judgments, strict=True)
        ),
        dissent=kept_dissent,
        sources=sum(judgment.sources for judgment in judgments),
    )
    return aggregated, dominated


def deflate_verdict(text_confidence: float, *, calibrated: float) -> str:
    """Verdict downgrading advice: escalate when self-report overclaims.

    Returns ``"escalate"`` when the self-reported confidence exceeds the
    calibrated confidence by more than 0.3, signalling that the judgment needs
    human or multi-source review; otherwise ``"accept"``.
    """
    calibrated_gap = _finite(text_confidence, "text_confidence") - _finite(calibrated, "calibrated")
    if calibrated_gap - _VERDICT_GAP > _FP_TOLERANCE:
        return "escalate"
    return "accept"

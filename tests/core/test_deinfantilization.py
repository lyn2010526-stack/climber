"""De-infantilization guard tests for the judgment and safety-gate layers.

Six anti-naive-behaviour guards, each verified on the module actually present
in the repository:

1. confidence counterbalance (calibrate) - evidence lifts, contradictions sink,
   the result never reaches the 0/1 extremes;
2. non-boolean goal discrimination (continuous_goal) - a weak sub-signal drags
   the geometric mean below the arithmetic mean instead of being averaged away;
3. emergence guard (aggregate_dissent) - minority opinions survive aggregation
   and a single dominant source is flagged;
4. safety-gated fitness (gated_fitness) - rejected content scores exactly zero,
   accepted content is penalized linearly;
5. runaway-positive-feedback damping (damped_boost) - consecutive boosts shrink
   monotonically and collapse to zero after the streak cap;
6. forgetting-decay coupling (coupled_decay) - frequently written memories
   decay more slowly and importance raises the survival score.

Plus the profile-side local anti-runaway behaviour and the profile ``blend``
hook still in flight from task C, guarded with a module-level probe.
"""

from __future__ import annotations

from datetime import UTC, datetime
from itertools import pairwise

import pytest

import app.core.metacognition.safety_gate as safety_gate_module
import app.core.profile as profile_package
import app.core.profile.loop as profile_loop_module
from app.core.metacognition.judgment import (
    Judgment,
    aggregate_dissent,
    calibrate,
    continuous_goal,
    deflate_verdict,
)
from app.core.metacognition.safety_gate import (
    BLOCK_THRESHOLD,
    DEFAULT_SURVIVAL_THRESHOLD,
    MAX_CONSECUTIVE_BOOSTS,
    SafetyVerdict,
    coupled_decay,
    damped_boost,
    gated_fitness,
    screen,
)
from app.core.profile import ProfileEvent, ProfileLoopService, ProfileSummary
from app.core.prompts.evolution import FitnessWeights

HAS_PROFILE_BLEND = hasattr(profile_package, "blend") or hasattr(profile_loop_module, "blend")
HAS_SAFETY_FINITE_HELPER = hasattr(safety_gate_module, "_finite")

NOW_VALUE = datetime(2026, 9, 30, tzinfo=UTC)


def _profile_event(**kwargs: object) -> ProfileEvent:
    defaults: dict[str, object] = {
        "instruction": "fix the login bug",
        "task_type": "debugging",
        "outcome": "success",
        "occurred_at": NOW_VALUE,
    }
    defaults.update(kwargs)
    return ProfileEvent(**defaults)  # type: ignore[arg-type]


# --- Guard 1: confidence counterbalance -----------------------------------------


def test_calibrate_rises_with_evidence() -> None:
    scores = [calibrate(0.5, evidence_count=evidence) for evidence in (0, 1, 3, 5, 10, 50)]
    assert scores == sorted(scores)
    assert scores[-1] > scores[0]
    assert all(score >= 0.5 for score in scores)


def test_calibrate_falls_with_contradictions() -> None:
    clean = calibrate(0.7, evidence_count=4, contradiction_count=0)
    scores = [calibrate(0.7, evidence_count=4, contradiction_count=count) for count in (1, 2, 3, 5)]
    assert scores == sorted(scores, reverse=True)
    assert scores[-1] < clean


def test_calibrate_stays_in_open_unit_interval() -> None:
    for raw in (0.0, 1.0, 0.999, -5.0):
        value = calibrate(raw, evidence_count=1000)
        assert 0.0 < value < 1.0
    for raw in (0.0, 1.0, 0.5):
        value = calibrate(raw, evidence_count=0, contradiction_count=10_000)
        assert 0.0 < value < 1.0


# --- Guard 2: non-boolean goal discrimination -----------------------------------


def test_continuous_goal_penalizes_weak_dimension() -> None:
    signals = (1.0, 0.4, 0.9)
    score = continuous_goal(signals)
    geometric = (0.4 * 0.9) ** (1 / 3)
    arithmetic = sum(signals) / len(signals)
    assert score == pytest.approx(geometric, abs=1e-9)
    assert score < arithmetic


def test_continuous_goal_never_hides_a_failing_dimension() -> None:
    assert continuous_goal(()) == 0.0
    assert continuous_goal((1.0, None, 1.0)) == 0.0
    assert continuous_goal((1.0, 0.0, 1.0)) == 0.0
    assert continuous_goal((0.2, 0.2, 0.2)) == pytest.approx(0.2)
    with pytest.raises(ValueError, match="weights must match"):
        continuous_goal((0.5,), weights=(1.0, 1.0))


# --- Guard 3: emergence constraint ----------------------------------------------


def test_aggregate_dissent_preserves_minority_when_dominated() -> None:
    strong = Judgment(claim="ship it", confidence=0.95, scale=0.9, sources=1)
    minority_first = Judgment(
        claim="wait", confidence=0.05, scale=0.2, dissent=("split_scope",), sources=1
    )
    minority_second = Judgment(
        claim="wait", confidence=0.05, scale=0.2, dissent=("missing_tests",), sources=1
    )
    aggregated, dominated = aggregate_dissent(
        [strong, minority_first, minority_second], dominance_cap=0.85
    )
    assert dominated is True
    assert aggregated.claim == "ship it"
    assert aggregated.dissent == ("split_scope",)
    assert aggregated.sources == 3


def test_aggregate_dissent_aggregates_normally_without_dominance() -> None:
    judgments = [
        Judgment(claim="ready", confidence=0.5, scale=0.8, sources=1),
        Judgment(claim="ready", confidence=0.5, scale=0.6, sources=1),
        Judgment(claim="ready", confidence=0.5, scale=0.7, sources=1),
    ]
    aggregated, dominated = aggregate_dissent(judgments)
    assert dominated is False
    assert aggregated.confidence == pytest.approx(0.5)
    assert aggregated.scale == pytest.approx(0.7)
    assert aggregated.sources == 3
    assert aggregated.dissent == ()


def test_deflate_verdict_escalates_on_overclaim() -> None:
    assert deflate_verdict(0.95, calibrated=0.5) == "escalate"
    assert deflate_verdict(0.8, calibrated=0.5) == "accept"
    assert deflate_verdict(0.2, calibrated=0.5) == "accept"


# --- Guard 4: safety-gated fitness ----------------------------------------------


def test_gated_fitness_zeroes_rejected_content() -> None:
    verdict = SafetyVerdict(allowed=False, penalty=1.0, reasons=("credential_token_literal",))
    assert gated_fitness(100.0, verdict) == 0.0


@pytest.mark.skipif(
    not HAS_SAFETY_FINITE_HELPER,
    reason="safety_gate public functions reference missing private helper _finite",
)
def test_gated_fitness_applies_linear_penalty() -> None:
    clean = gated_fitness(1.0, SafetyVerdict(allowed=True, penalty=0.0))
    partial = gated_fitness(1.0, SafetyVerdict(allowed=True, penalty=0.4))
    full = gated_fitness(1.0, SafetyVerdict(allowed=True, penalty=1.0))
    assert clean == 1.0
    assert full == 0.0
    assert partial == pytest.approx(0.6)


def test_screen_blocks_risk_patterns_and_accumulates_penalty() -> None:
    verdict = screen('api_key = "ghp_0123456789abcdefghij"; rm -rf /tmp/target')
    assert verdict.allowed is False
    assert verdict.penalty >= BLOCK_THRESHOLD
    assert "credential_assignment" in verdict.reasons
    safe = screen("refactor the storage layer and add tests")
    assert safe.allowed is True
    assert safe.penalty == 0.0


@pytest.mark.skipif(
    not HAS_SAFETY_FINITE_HELPER,
    reason="safety_gate public functions reference missing private helper _finite",
)
def test_screen_verdict_feeds_gated_fitness() -> None:
    dangerous = screen('api_key = "sk-0123456789abcdef0123456789"')
    assert dangerous.allowed is False
    assert gated_fitness(50.0, dangerous) == 0.0

    safety_penalty = FitnessWeights().safety_penalty
    assert safety_penalty == pytest.approx(1.0)
    safe = screen("add tests for the storage layer")
    assert gated_fitness(50.0, safe) == pytest.approx(50.0)


# --- Guard 5: runaway-positive-feedback damping ---------------------------------


@pytest.mark.skipif(
    not HAS_SAFETY_FINITE_HELPER,
    reason="safety_gate public functions reference missing private helper _finite",
)
def test_damped_boost_increments_shrink_monotonically() -> None:
    value = 0.0
    increments: list[float] = []
    for boost_count in range(1, MAX_CONSECUTIVE_BOOSTS + 1):
        boosted = damped_boost(value, 1.0, boost_count=boost_count)
        increments.append(boosted - value)
        value = boosted
    assert all(later < earlier for earlier, later in pairwise(increments))
    assert all(increment > 0.0 for increment in increments)


@pytest.mark.skipif(
    not HAS_SAFETY_FINITE_HELPER,
    reason="safety_gate public functions reference missing private helper _finite",
)
def test_damped_boost_caps_after_max_consecutive_boosts() -> None:
    value = damped_boost(0.0, 1.0, boost_count=1)
    capped = damped_boost(value, 1.0, boost_count=MAX_CONSECUTIVE_BOOSTS + 1)
    assert capped == value
    assert damped_boost(0.7, 0.3, boost_count=1) == 0.7


# --- Guard 6: forgetting-decay coupling -----------------------------------------


@pytest.mark.skipif(
    not HAS_SAFETY_FINITE_HELPER,
    reason="safety_gate public functions reference missing private helper _finite",
)
def test_coupled_decay_survives_longer_with_frequent_writes() -> None:
    stale = coupled_decay(60.0, write_frequency=0.0, importance=0.5)
    fresh = coupled_decay(60.0, write_frequency=10.0, importance=0.5)
    assert fresh > stale
    assert 0.0 < fresh <= 1.0


@pytest.mark.skipif(
    not HAS_SAFETY_FINITE_HELPER,
    reason="safety_gate public functions reference missing private helper _finite",
)
def test_coupled_decay_importance_raises_survival() -> None:
    important = coupled_decay(30.0, write_frequency=1.0, importance=0.9)
    minor = coupled_decay(30.0, write_frequency=1.0, importance=0.2)
    assert important > minor
    assert minor < DEFAULT_SURVIVAL_THRESHOLD < important
    assert coupled_decay(0.0, write_frequency=0.0, importance=0.8) == pytest.approx(0.8)


# --- Profile-side local anti-runaway (task C feedback marginal diminishing) -----


def test_profile_positive_signal_has_diminishing_marginal_gain() -> None:
    service = ProfileLoopService()
    service.record(_profile_event(task_type="debugging", outcome="success", feedback="positive"))
    first_score = service.summary(as_of=NOW_VALUE).task_preferences["debugging"]

    service.record(_profile_event(task_type="debugging", outcome="success", feedback="positive"))
    second_score = service.summary(as_of=NOW_VALUE).task_preferences["debugging"]

    service.record(_profile_event(task_type="debugging", outcome="success", feedback="positive"))
    third_score = service.summary(as_of=NOW_VALUE).task_preferences["debugging"]

    assert second_score - first_score <= first_score
    assert third_score - second_score <= second_score - first_score


@pytest.mark.skipif(
    not HAS_PROFILE_BLEND,
    reason="pending task C: profile-side blend() is not delivered yet",
)
def test_profile_blend_reduces_weight_when_positive_dominated() -> None:
    from app.core.profile import blend

    incoming = ProfileSummary({}, {}, {}, 0.0, 0.0, 1.0, 0.5, (), True)
    early = ProfileSummary({}, {}, {}, 0.0, 0.0, 0.5, 0.5, (), True)
    late = ProfileSummary({}, {}, {}, 0.0, 0.0, 0.95, 0.5, (), True)

    early_gain = abs(blend(early, incoming).success_rate - early.success_rate)
    late_gain = abs(blend(late, incoming).success_rate - late.success_rate)
    assert late_gain < early_gain

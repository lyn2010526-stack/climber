"""Tests for the judgment layer (calibration, continuous goals, dissent)."""

from __future__ import annotations

import dataclasses
import math

import pytest

from app.core.metacognition import (
    Judgment,
    aggregate_dissent,
    calibrate,
    continuous_goal,
    deflate_verdict,
)


class TestCalibrate:
    @pytest.mark.parametrize("raw", [math.nan, math.inf, -math.inf])
    def test_non_finite_raw_confidence_raises(self, raw):
        with pytest.raises(ValueError, match="finite"):
            calibrate(raw, evidence_count=0)
    def test_empty_evidence_keeps_base_within_bounds(self):
        assert calibrate(0.5, evidence_count=0) == pytest.approx(0.5)

    def test_extreme_raw_values_are_clamped_away_from_zero_and_one(self):
        assert calibrate(0.0, evidence_count=0) == pytest.approx(0.05)
        assert calibrate(1.0, evidence_count=0) == pytest.approx(0.95)

    def test_extreme_raw_values_stay_in_bounds_even_with_evidence(self):
        assert calibrate(0.0, evidence_count=1_000_000) < 0.95
        assert calibrate(1.0, evidence_count=1_000_000) == pytest.approx(0.95)

    def test_more_evidence_raises_confidence_monotonically(self):
        values = [calibrate(0.5, evidence_count=n) for n in (0, 1, 3, 10, 50, 1000)]
        assert values == sorted(values)
        assert values[-1] < 0.95

    def test_evidence_boost_has_diminishing_returns(self):
        increment_early = calibrate(0.5, evidence_count=100) - calibrate(0.5, evidence_count=10)
        increment_late = calibrate(0.5, evidence_count=10_000) - calibrate(
            0.5, evidence_count=1_000
        )
        assert increment_late < increment_early

    def test_contradictions_lower_confidence_multiplicatively(self):
        values = [calibrate(0.8, evidence_count=5, contradiction_count=n) for n in (0, 1, 2, 5, 10)]
        assert values == sorted(values, reverse=True)
        assert values[-1] >= 0.05

    def test_all_contradictions_hit_floor(self):
        assert calibrate(0.9, evidence_count=0, contradiction_count=100) == pytest.approx(0.05)

    def test_result_always_within_bounds(self):
        for raw in (-1.0, 0.0, 0.3, 0.7, 1.0, 2.0):
            for evidence in (0, 7):
                for contradictions in (0, 9):
                    value = calibrate(
                        raw, evidence_count=evidence, contradiction_count=contradictions
                    )
                    assert 0.05 <= value <= 0.95

    def test_negative_counts_treated_as_zero(self):
        assert calibrate(0.5, evidence_count=-3) == pytest.approx(0.5)
        assert calibrate(0.5, evidence_count=0, contradiction_count=-1) == pytest.approx(0.5)


class TestContinuousGoal:
    @pytest.mark.parametrize("signal", [math.nan, math.inf, -math.inf])
    def test_non_finite_signal_raises(self, signal):
        with pytest.raises(ValueError, match="finite"):
            continuous_goal([signal])

    def test_non_finite_weight_raises(self):
        with pytest.raises(ValueError, match="finite"):
            continuous_goal([0.5], weights=[math.nan])
    def test_empty_signals_yield_zero(self):
        assert continuous_goal([]) == 0.0

    def test_missing_signals_yield_zero(self):
        assert continuous_goal([None, 0.8, 0.9]) == 0.0
        assert continuous_goal([0.8, None]) == 0.0

    def test_all_full_signals_yield_one(self):
        assert continuous_goal([1.0, 1.0, 1.0]) == pytest.approx(1.0)

    def test_shortboard_punished_harder_than_arithmetic_mean(self):
        signals = [1.0, 0.1]
        geo = continuous_goal(signals)
        arithmetic = sum(signals) / len(signals)
        assert geo < arithmetic
        assert 0.0 < geo < 1.0

    def test_single_zero_signal_zeroes_attainment(self):
        assert continuous_goal([0.9, 0.9, 0.0]) == 0.0

    def test_equal_weights_match_default(self):
        signals = [0.4, 0.9]
        assert continuous_goal(signals, weights=[1.0, 1.0]) == pytest.approx(
            continuous_goal(signals)
        )

    def test_weighted_extreme_weight_dominates(self):
        signals = [0.0, 1.0]
        assert continuous_goal(signals, weights=[1.0, 0.0]) == 0.0
        assert continuous_goal(signals, weights=[0.0, 1.0]) == pytest.approx(1.0)

    def test_weights_length_mismatch_raises(self):
        with pytest.raises(ValueError, match="length"):
            continuous_goal([0.5, 0.5], weights=[1.0])

    def test_negative_weight_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            continuous_goal([0.5], weights=[-1.0])

    def test_all_zero_weights_raise(self):
        with pytest.raises(ValueError, match="zero"):
            continuous_goal([0.5, 0.5], weights=[0.0, 0.0])

    def test_out_of_range_signals_are_clamped(self):
        assert continuous_goal([2.0, 1.0]) == pytest.approx(1.0)
        assert continuous_goal([-0.5, 1.0]) == 0.0


class TestAggregateDissent:
    def test_empty_input_raises(self):
        with pytest.raises(ValueError, match="empty"):
            aggregate_dissent([])

    def test_invalid_dominance_cap_raises(self):
        judgment = Judgment(claim="c", confidence=0.5, scale=0.5)
        with pytest.raises(ValueError, match="dominance_cap"):
            aggregate_dissent([judgment], dominance_cap=0.0)
        with pytest.raises(ValueError, match="dominance_cap"):
            aggregate_dissent([judgment], dominance_cap=1.5)

    def test_single_judgment_holds_full_share(self):
        judgment = Judgment(claim="only", confidence=0.9, scale=1.0, sources=2)
        aggregated, dominated = aggregate_dissent([judgment])
        assert dominated is True
        assert aggregated.claim == "only"
        assert aggregated.confidence == pytest.approx(0.9)
        assert aggregated.sources == 2

    def test_dominance_triggers_when_one_signal_overwhelms(self):
        dominant = Judgment(claim="strong", confidence=0.99, scale=0.9, sources=1)
        weak_a = Judgment(claim="weak-a", confidence=0.05, scale=0.2, sources=1)
        weak_b = Judgment(claim="weak-b", confidence=0.05, scale=0.2, sources=1)
        aggregated, dominated = aggregate_dissent([weak_a, weak_b, dominant])
        assert dominated is True
        assert aggregated.claim == "strong"

    def test_dominance_not_triggered_for_balanced_sources(self):
        judgments = [
            Judgment(claim=f"claim-{i}", confidence=0.5, scale=0.5, sources=1) for i in range(4)
        ]
        aggregated, dominated = aggregate_dissent(judgments)
        assert dominated is False
        assert aggregated.claim == "claim-0"
        assert aggregated.confidence == pytest.approx(0.5)

    def test_share_exactly_at_cap_is_not_dominance(self):
        top = Judgment(claim="top", confidence=0.85, scale=0.5)
        other = Judgment(claim="other", confidence=0.15, scale=0.5)
        _, dominated = aggregate_dissent([top, other], dominance_cap=0.85)
        assert dominated is False

    def test_most_voted_dissent_survives(self):
        judgments = [
            Judgment("a", 0.4, 0.5, dissent=("keep-me", "noise")),
            Judgment("b", 0.3, 0.5, dissent=("keep-me",)),
            Judgment("c", 0.3, 0.5, dissent=("noise", "other-voice")),
        ]
        aggregated, _ = aggregate_dissent(judgments)
        assert aggregated.dissent == ("keep-me",)

    def test_dissent_tie_keeps_first_seen(self):
        judgments = [
            Judgment("a", 0.5, 0.5, dissent=("first",)),
            Judgment("b", 0.5, 0.5, dissent=("second",)),
        ]
        aggregated, _ = aggregate_dissent(judgments)
        assert aggregated.dissent == ("first",)

    def test_no_dissent_yields_empty_tuple(self):
        judgments = [Judgment("a", 0.5, 0.5), Judgment("b", 0.5, 0.5)]
        aggregated, _ = aggregate_dissent(judgments)
        assert aggregated.dissent == ()

    def test_aggregated_sources_are_summed_and_scale_averaged(self):
        judgments = [
            Judgment("a", 0.75, 0.8, sources=3),
            Judgment("b", 0.25, 0.4, sources=1),
        ]
        aggregated, _ = aggregate_dissent(judgments)
        assert aggregated.sources == 4
        expected_scale = 0.75 * 0.8 + 0.25 * 0.4
        assert aggregated.scale == pytest.approx(expected_scale)

    def test_all_zero_confidence_falls_back_to_equal_shares(self):
        judgments = [
            Judgment("a", 0.0, 0.5, sources=1),
            Judgment("b", 0.0, 0.5, sources=1),
        ]
        aggregated, dominated = aggregate_dissent(judgments)
        assert dominated is False
        assert aggregated.confidence == pytest.approx(0.0)
        assert aggregated.claim == "a"


class TestDeflateVerdict:
    def test_non_finite_confidence_raises(self):
        with pytest.raises(ValueError, match="finite"):
            deflate_verdict(math.nan, calibrated=0.5)
    def test_overclaiming_escalates(self):
        assert deflate_verdict(0.9, calibrated=0.5) == "escalate"
        assert deflate_verdict(0.95, calibrated=0.3) == "escalate"

    def test_honest_confidence_accepts(self):
        assert deflate_verdict(0.5, calibrated=0.5) == "accept"
        assert deflate_verdict(0.7, calibrated=0.5) == "accept"

    def test_boundary_gap_of_point_three_accepts(self):
        assert deflate_verdict(0.8, calibrated=0.5) == "accept"

    def test_just_over_boundary_escalates(self):
        assert deflate_verdict(0.81, calibrated=0.5) == "escalate"

    def test_underconfidence_still_accepts(self):
        assert deflate_verdict(0.1, calibrated=0.9) == "accept"


class TestJudgment:
    def test_non_finite_values_raise(self):
        with pytest.raises(ValueError, match="finite"):
            Judgment(claim="c", confidence=math.nan, scale=0.5)
    def test_confidence_out_of_range_raises(self):
        with pytest.raises(ValueError, match="confidence"):
            Judgment(claim="c", confidence=1.5, scale=0.5)
        with pytest.raises(ValueError, match="confidence"):
            Judgment(claim="c", confidence=-0.1, scale=0.5)

    def test_scale_out_of_range_raises(self):
        with pytest.raises(ValueError, match="scale"):
            Judgment(claim="c", confidence=0.5, scale=1.5)
        with pytest.raises(ValueError, match="scale"):
            Judgment(claim="c", confidence=0.5, scale=-0.5)

    def test_negative_sources_raises(self):
        with pytest.raises(ValueError, match="sources"):
            Judgment(claim="c", confidence=0.5, scale=0.5, sources=-1)

    def test_frozen_and_slotted(self):
        judgment = Judgment(claim="c", confidence=0.5, scale=0.5)
        assert dataclasses.is_dataclass(judgment)
        with pytest.raises(dataclasses.FrozenInstanceError):
            judgment.claim = "other"
        assert not hasattr(judgment, "__dict__")

    def test_dict_roundtrip(self):
        judgment = Judgment("claim", 0.6, 0.7, dissent=("d1", "d2"), sources=4)
        payload = judgment.to_dict()
        restored = Judgment.from_dict(payload)
        assert restored == judgment

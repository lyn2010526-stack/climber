"""Coverage tests for app.core.engine.router_decision.

Self-contained, deterministic, no network / external services.
"""

from __future__ import annotations

import pytest

from app.core.engine.router_decision import (
    RouterDecisionEngine,
    RouterDecisionEvent,
    TierConfig,
)


def _engine() -> RouterDecisionEngine:
    return RouterDecisionEngine()


# --------------------------------------------------------------------------- #
# Dataclasses
# --------------------------------------------------------------------------- #
def test_router_decision_event_to_dict():
    event = RouterDecisionEvent(
        target_tier="C2",
        model="m",
        provider="p",
        confidence=0.81234,
        probabilities={"C1": 0.5, "C2": 0.5},
        savings_pct=12.5,
        fallback_reason="fallback from C3",
        route_source="classifier",
        latency_ms=1.2345,
        task_complexity=0.4567,
    )
    d = event.to_dict()
    assert d["target_tier"] == "C2"
    assert d["confidence"] == 0.8123
    assert d["probabilities"] == {"C1": 0.5, "C2": 0.5}
    assert d["savings_pct"] == 12.5
    assert d["fallback_reason"] == "fallback from C3"
    assert d["latency_ms"] == 1.23
    assert d["task_complexity"] == 0.457


def test_tier_config_defaults():
    tier = TierConfig(name="t", models=[("p", "m")])
    assert tier.max_tokens == 4096
    assert tier.cost_per_1k == 0.01
    assert tier.capability_score == 0.5


def test_default_tiers_structure():
    tiers = RouterDecisionEngine._default_tiers()
    assert set(tiers) == {"C0", "C1", "C2", "C3"}
    assert tiers["C3"].cost_per_1k == 0.10


# --------------------------------------------------------------------------- #
# estimate_complexity
# --------------------------------------------------------------------------- #
def test_estimate_complexity_length_buckets():
    eng = _engine()
    assert eng.estimate_complexity("short") == pytest.approx(0.1)
    assert eng.estimate_complexity("a" * 100) == pytest.approx(0.2)
    assert eng.estimate_complexity("a" * 500) == pytest.approx(0.3)
    assert eng.estimate_complexity("a" * 1500) == pytest.approx(0.4)


def test_estimate_complexity_tool_buckets():
    eng = _engine()
    assert eng.estimate_complexity("x") == pytest.approx(0.1)
    assert eng.estimate_complexity("x", tool_count=1) == pytest.approx(0.2)
    assert eng.estimate_complexity("x", tool_count=3) == pytest.approx(0.3)
    assert eng.estimate_complexity("x", tool_count=6) == pytest.approx(0.4)


def test_estimate_complexity_history_buckets():
    eng = _engine()
    assert eng.estimate_complexity("x", history_len=6) == pytest.approx(0.2)
    assert eng.estimate_complexity("x", history_len=11) == pytest.approx(0.3)


def test_estimate_complexity_keyword_boost_and_clamp():
    eng = _engine()
    boosted = eng.estimate_complexity("please analyze this")
    assert boosted == pytest.approx(0.25)
    clamped = eng.estimate_complexity(
        "arch" + "a" * 1500 + " analyze plan design", tool_count=10, history_len=20
    )
    assert clamped == 1.0


# --------------------------------------------------------------------------- #
# select_tier
# --------------------------------------------------------------------------- #
def test_select_tier_default_boundaries():
    eng = _engine()
    assert eng.select_tier(0.19) == "C0"
    assert eng.select_tier(0.2) == "C1"
    assert eng.select_tier(0.44) == "C1"
    assert eng.select_tier(0.45) == "C2"
    assert eng.select_tier(0.69) == "C2"
    assert eng.select_tier(0.7) == "C3"


def test_select_tier_empty_tiers_returns_c1():
    eng = _engine()
    eng._tiers = {}
    assert eng.select_tier(0.5) == "C1"


def test_select_tier_clamps_down_to_available():
    eng = RouterDecisionEngine(tiers={"C1": TierConfig(name="s", models=[("p", "m")])})
    assert eng.select_tier(0.9) == "C1"


def test_select_tier_falls_back_to_lowest_available():
    eng = RouterDecisionEngine(tiers={"C2": TierConfig(name="e", models=[("p", "m")])})
    assert eng.select_tier(0.05) == "C2"


# --------------------------------------------------------------------------- #
# decide
# --------------------------------------------------------------------------- #
def test_decide_classifier_defaults():
    eng = _engine()
    event = eng.decide("hello there")
    assert event.target_tier == "C0"
    assert event.route_source == "classifier"
    assert event.provider == "openai"
    assert event.model == "gpt-4o-mini"
    assert event.fallback_reason is None
    assert event.savings_pct == pytest.approx(99.0)
    assert sum(event.probabilities.values()) == pytest.approx(1.0)


def test_decide_user_override():
    eng = _engine()
    event = eng.decide("hello", user_override="C3")
    assert event.target_tier == "C3"
    assert event.route_source == "user_override"
    assert event.confidence == 1.0
    assert event.provider == "anthropic"


def test_decide_invalid_override_falls_back_to_classifier():
    eng = _engine()
    event = eng.decide("hello", user_override="NOPE")
    assert event.route_source == "classifier"
    assert event.target_tier == "C0"


def test_decide_available_models_match():
    eng = _engine()
    event = eng.decide(
        "hello",
        available_models=[("openai", "gpt-4o-mini"), ("anthropic", "x")],
    )
    assert event.route_source == "classifier"
    assert event.model == "gpt-4o-mini"


def test_decide_available_models_no_match_marks_fallback():
    eng = _engine()
    event = eng.decide("hello", available_models=[("other", "model")])
    assert event.route_source == "fallback"
    # Falls back to the first configured model of the tier.
    assert event.model == "gpt-4o-mini"


def test_decide_fallback_reason_from_previous_tier():
    eng = _engine()
    event = eng.decide("hello", user_override="C3", previous_tier="C1")
    assert event.fallback_reason == "fallback from C1"

    same = eng.decide("hello", user_override="C3", previous_tier="C3")
    assert same.fallback_reason is None


def test_decide_probabilities_and_savings():
    eng = _engine()
    event = eng.decide("x" * 1500, tool_count=6)  # 0.4 + 0.3 -> C3
    assert event.target_tier == "C3"
    assert event.savings_pct == 0.0  # C3 is the most expensive tier
    # target tier gets the confidence, the rest share (1-confidence)/(n-1)
    assert event.probabilities["C3"] == pytest.approx(event.confidence)
    others = [v for k, v in event.probabilities.items() if k != "C3"]
    assert all(v == pytest.approx((1 - event.confidence) / 3) for v in others)


# --------------------------------------------------------------------------- #
# decision log / stats
# --------------------------------------------------------------------------- #
def test_decision_log_and_cap():
    eng = _engine()
    eng._max_log_size = 2
    for _ in range(3):
        eng.decide("hello")
    log = eng.get_decision_log()
    # On overflow the log keeps the last max//2 entries.
    assert len(log) == 1

    eng._max_log_size = 1000
    eng.decide("hello")
    assert len(eng.get_decision_log(last_n=1)) == 1


def test_get_stats_empty():
    eng = _engine()
    assert eng.get_stats() == {"total_decisions": 0}


def test_get_stats_populated():
    eng = _engine()
    eng.decide("hello")  # C0 classifier
    eng.decide("hello", user_override="C3")  # C3 user_override
    stats = eng.get_stats()
    assert stats["total_decisions"] == 2
    assert stats["tier_distribution"] == {"C0": 1, "C3": 1}
    assert stats["source_distribution"] == {"classifier": 1, "user_override": 1}
    assert 0 <= stats["avg_confidence"] <= 1
    assert stats["avg_savings_pct"] >= 0

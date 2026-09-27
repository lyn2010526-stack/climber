"""RouterDecisionEngine regression tests.

Pins the tiered model-routing contract (C0-C3) and cost-optimization
behavior. Previously 0% coverage. Protects the model-scheduling layer
against silent regressions that would break cost/quality balance.
"""

from __future__ import annotations

import pytest

from app.core.engine.router_decision import RouterDecisionEngine, RouterDecisionEvent, TierConfig


@pytest.fixture
def engine() -> RouterDecisionEngine:
    return RouterDecisionEngine()


def test_default_tiers_exist(engine: RouterDecisionEngine) -> None:
    tiers = engine._tiers
    assert set(tiers) == {"C0", "C1", "C2", "C3"}
    assert tiers["C3"].capability_score > tiers["C0"].capability_score


def test_estimate_complexity_scales_with_length(engine: RouterDecisionEngine) -> None:
    short = engine.estimate_complexity("hi")
    long = engine.estimate_complexity("x" * 1200)
    assert long > short
    assert 0 <= long <= 1.0


def test_estimate_complexity_tool_boost(engine: RouterDecisionEngine) -> None:
    with_tools = engine.estimate_complexity("help", tool_count=8)
    without = engine.estimate_complexity("help")
    assert with_tools > without


def test_estimate_complexity_history_boost(engine: RouterDecisionEngine) -> None:
    deep = engine.estimate_complexity("help", history_len=20)
    shallow = engine.estimate_complexity("help", history_len=1)
    assert deep > shallow


def test_estimate_complexity_keyword_boost(engine: RouterDecisionEngine) -> None:
    plain = engine.estimate_complexity("tell me a fact")
    complex_score = engine.estimate_complexity("design the architecture for a refactor")
    assert complex_score > plain


def test_select_tier_boundaries(engine: RouterDecisionEngine) -> None:
    assert engine.select_tier(0.05) == "C0"
    assert engine.select_tier(0.3) == "C1"
    assert engine.select_tier(0.5) == "C2"
    assert engine.select_tier(0.95) == "C3"


def test_select_tier_clamps_when_tier_missing() -> None:
    engine = RouterDecisionEngine(tiers={"C0": TierConfig("ultra_light", [("x", "y")])})
    assert engine.select_tier(0.95) == "C0"  # clamped down to nearest available


def test_select_tier_custom_without_c3_clamps() -> None:
    # NOTE: tiers={} is falsy and falls back to defaults via `tiers or default`.
    # A partial custom config without C3 must clamp C3-requests to nearest tier.
    engine = RouterDecisionEngine(
        tiers={"C1": TierConfig("standard", [("x", "y")]), "C2": TierConfig("enhanced", [("x", "y")])}
    )
    assert engine.select_tier(0.95) == "C2"  # C3 requested, clamped to highest available


def test_decide_returns_event_shape(engine: RouterDecisionEngine) -> None:
    event = engine.decide("hello there")
    assert isinstance(event, RouterDecisionEvent)
    assert event.to_dict()["target_tier"] in {"C0", "C1", "C2", "C3"}
    assert event.to_dict()["confidence"] >= 0.0


def test_decide_user_override(engine: RouterDecisionEngine) -> None:
    event = engine.decide("hello", user_override="C3")
    assert event.target_tier == "C3"
    assert event.route_source == "user_override"
    assert event.confidence == 1.0


def test_decide_user_override_ignored_if_invalid(engine: RouterDecisionEngine) -> None:
    event = engine.decide("hello", user_override="C9")
    assert event.target_tier != "C9"
    assert event.route_source == "classifier"


def test_decide_available_models_match(engine: RouterDecisionEngine) -> None:
    # Long message + tools + history + keywords pushes complexity to C3.
    message = ("Please analyze and design the full architecture for a large refactor " * 5)
    available = [("anthropic", "claude-opus-4-20250514")]
    event = engine.decide(message, available_models=available, tool_count=8, history_len=20)
    assert event.target_tier == "C3"
    assert event.model == "claude-opus-4-20250514"
    assert event.route_source != "fallback"


def test_decide_available_models_miss_falls_back(engine: RouterDecisionEngine) -> None:
    available = [("custom", "some-other-model")]
    event = engine.decide("hello", available_models=available)
    assert event.route_source == "fallback"


def test_decide_savings_vs_most_expensive(engine: RouterDecisionEngine) -> None:
    cheap = engine.decide("hi")
    assert cheap.savings_pct > 0  # routing to a cheaper tier saves vs C3


def test_decide_previous_tier_fallback_reason(engine: RouterDecisionEngine) -> None:
    event = engine.decide("hi", previous_tier="C3")
    assert event.fallback_reason is not None
    assert "C3" in event.fallback_reason


def test_decide_probabilities_sum_to_one(engine: RouterDecisionEngine) -> None:
    event = engine.decide("hello world")
    total = sum(event.probabilities.values())
    assert total == pytest.approx(1.0, abs=1e-6)


def test_decision_log_and_stats(engine: RouterDecisionEngine) -> None:
    assert engine.get_stats() == {"total_decisions": 0}
    engine.decide("one")
    engine.decide("two", user_override="C2")
    stats = engine.get_stats()
    assert stats["total_decisions"] == 2
    assert set(stats["tier_distribution"].keys()) <= {"C0", "C1", "C2", "C3"}
    assert stats["source_distribution"].get("classifier") >= 1
    assert stats["source_distribution"].get("user_override") == 1


def test_decision_log_size_cap() -> None:
    engine = RouterDecisionEngine()
    engine._max_log_size = 20
    for i in range(50):
        engine.decide(f"message number {i}")
    assert len(engine.get_decision_log(last_n=100)) <= 20


def test_custom_tier_config_respected() -> None:
    tiers = {
        "C1": TierConfig("standard", [("openai", "gpt-4o-mini")], max_tokens=1024, cost_per_1k=0.005, capability_score=0.4),
    }
    engine = RouterDecisionEngine(tiers=tiers)
    event = engine.decide("hello there friend")
    assert event.target_tier == "C1"
    assert event.model == "gpt-4o-mini"

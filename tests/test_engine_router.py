"""Tests for router decision engine."""

import pytest

from app.core.engine.router_decision import (
    RouterDecisionEngine,
    RouterDecisionEvent,
    TierConfig,
)


class TestRouterDecisionEngine:
    def test_default_tiers_exist(self) -> None:
        engine = RouterDecisionEngine()
        assert "C0" in engine._tiers
        assert "C3" in engine._tiers

    def test_estimate_complexity_simple(self) -> None:
        engine = RouterDecisionEngine()
        score = engine.estimate_complexity("Hi", tool_count=0, history_len=0)
        assert 0.0 <= score <= 0.3

    def test_estimate_complexity_complex(self) -> None:
        engine = RouterDecisionEngine()
        score = engine.estimate_complexity(
            "Implement a comprehensive microservice architecture with refactoring",
            tool_count=8,
            history_len=15,
        )
        assert score >= 0.5

    def test_select_tier_c0(self) -> None:
        engine = RouterDecisionEngine()
        assert engine.select_tier(0.1) == "C0"

    def test_select_tier_c3(self) -> None:
        engine = RouterDecisionEngine()
        assert engine.select_tier(0.9) == "C3"

    def test_decide_returns_event(self) -> None:
        engine = RouterDecisionEngine()
        event = engine.decide("Write a Python function", tool_count=3)
        assert isinstance(event, RouterDecisionEvent)
        assert event.model != ""
        assert event.provider != ""
        assert 0.0 <= event.confidence <= 1.0
        assert event.target_tier in ["C0", "C1", "C2", "C3"]

    def test_decide_logs_decision(self) -> None:
        engine = RouterDecisionEngine()
        engine.decide("test message")
        assert len(engine._decision_log) == 1

    def test_decide_user_override(self) -> None:
        engine = RouterDecisionEngine()
        event = engine.decide("Hi", user_override="C3")
        assert event.target_tier == "C3"
        assert event.route_source == "user_override"

    def test_decide_savings(self) -> None:
        engine = RouterDecisionEngine()
        event = engine.decide("Hi")
        # C0/C1 should have savings > 0
        if event.target_tier in ("C0", "C1"):
            assert event.savings_pct > 0

    def test_decision_log_size_cap(self) -> None:
        engine = RouterDecisionEngine()
        engine._max_log_size = 10
        for i in range(15):
            engine.decide(f"message {i}")
        assert len(engine._decision_log) <= 10

    def test_get_stats(self) -> None:
        engine = RouterDecisionEngine()
        for i in range(5):
            engine.decide(f"test message {i}")
        stats = engine.get_stats()
        assert stats["total_decisions"] == 5
        assert "tier_distribution" in stats
        assert "avg_confidence" in stats

    def test_custom_tiers(self) -> None:
        tiers = {
            "C0": TierConfig(name="fast", models=[("openai", "gpt-4o-mini")]),
            "C1": TierConfig(name="standard", models=[("openai", "gpt-4o")]),
        }
        engine = RouterDecisionEngine(tiers=tiers)
        # Complex message routes to C1 which has gpt-4o
        event = engine.decide(
            "Implement a comprehensive refactoring plan with detailed architecture analysis",
            available_models=[("openai", "gpt-4o")],
            tool_count=5,
            history_len=10,
        )
        assert event.model == "gpt-4o"
        assert event.target_tier == "C1"

    def test_event_to_dict(self) -> None:
        event = RouterDecisionEvent(
            target_tier="C2",
            model="gpt-4o",
            provider="openai",
            confidence=0.85,
            probabilities={"C1": 0.1, "C2": 0.85, "C3": 0.05},
        )
        d = event.to_dict()
        assert d["target_tier"] == "C2"
        assert "decision_id" in d
        assert isinstance(d["probabilities"], dict)


class TestRouterDecisionEvent:
    def test_auto_fields(self) -> None:
        event = RouterDecisionEvent(model="gpt-4o", provider="openai")
        assert len(event.decision_id) == 12
        assert event.timestamp > 0

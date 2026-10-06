"""Coverage tests for app/core/collaboration/aggregation.py."""

from __future__ import annotations

from app.core.collaboration.aggregation import (
    AgentResult,
    AggregationResult,
    AggregationStrategy,
    ResultAggregator,
)


def _result(
    agent_id: str,
    result: object,
    confidence: float,
    task_id: str = "task-1",
) -> AgentResult:
    return AgentResult(
        agent_id=agent_id,
        task_id=task_id,
        result=result,
        confidence=confidence,
        metadata={"k": agent_id},
    )


def test_agent_result_to_dict_roundtrip() -> None:
    r = _result("a", "value", 0.7)
    data = r.to_dict()
    assert data["agent_id"] == "a"
    assert data["result"] == "value"
    assert data["confidence"] == 0.7
    assert data["metadata"] == {"k": "a"}
    assert isinstance(data["timestamp"], float)


def test_aggregation_result_to_dict() -> None:
    ar = AggregationResult(
        task_id="t",
        consensus_reached=True,
        consensus_value=42,
        strategy=AggregationStrategy.WEIGHTED_AVERAGE,
        results=[_result("a", 42, 0.9)],
        divergence_detected=False,
    )
    data = ar.to_dict()
    assert data["task_id"] == "t"
    assert data["consensus_reached"] is True
    assert data["strategy"] == "weighted_average"
    assert data["result_count"] == 1
    assert isinstance(data["aggregation_id"], str)


def test_add_and_get_results() -> None:
    agg = ResultAggregator()
    agg.add_result(_result("a", "x", 0.5))
    agg.add_result(_result("b", "y", 0.6))
    assert len(agg.get_results("task-1")) == 2
    assert agg.get_results("missing") == []


def test_aggregate_empty_returns_no_consensus() -> None:
    agg = ResultAggregator()
    out = agg.aggregate("nothing")
    assert out.consensus_reached is False
    assert out.results == []
    assert out.strategy == AggregationStrategy.BEST_CONFIDENCE


def test_majority_vote_consensus_and_divergence() -> None:
    agg = ResultAggregator(consensus_threshold=0.6)
    agg.add_result(_result("a", "yes", 0.9))
    agg.add_result(_result("b", "yes", 0.8))
    agg.add_result(_result("c", "no", 0.7))
    out = agg.get_consensus("task-1")
    assert out.consensus_reached is True
    assert out.consensus_value == "yes"
    assert out.divergence_detected is True
    assert out.divergent_agents == ["c"]
    assert len(out.results) == 3


def test_majority_vote_no_consensus() -> None:
    agg = ResultAggregator(consensus_threshold=0.9)
    agg.add_result(_result("a", "yes", 0.9))
    agg.add_result(_result("b", "no", 0.8))
    out = agg.get_consensus("task-1")
    assert out.consensus_reached is False
    # largest group is the single "yes" vote; the lone dissenter is divergent
    assert out.divergent_agents == ["b"]


def test_majority_vote_empty_groups_direct() -> None:
    agg = ResultAggregator()
    out = agg._majority_vote("task-x", [])
    assert out.consensus_reached is False
    assert out.strategy == AggregationStrategy.MAJORITY_VOTE


def test_weighted_average_numeric() -> None:
    agg = ResultAggregator(consensus_threshold=0.5)
    agg.add_result(_result("a", 10, 1.0))
    agg.add_result(_result("b", 11, 1.0))
    out = agg.get_weighted_result("task-1")
    assert out.strategy == AggregationStrategy.WEIGHTED_AVERAGE
    assert out.consensus_value == 10.5
    # spread 1 <= tolerance max(10.5*0.1, 1e-9) -> consensus
    assert out.consensus_reached is True


def test_weighted_average_divergence_when_spread_large() -> None:
    agg = ResultAggregator(consensus_threshold=0.5)
    agg.add_result(_result("a", 1, 1.0))
    agg.add_result(_result("b", 100, 1.0))
    out = agg.get_weighted_result("task-1")
    assert out.consensus_reached is False
    assert out.divergence_detected is True
    assert set(out.divergent_agents) == {"a", "b"}


def test_weighted_average_falls_back_when_no_numeric() -> None:
    agg = ResultAggregator()
    agg.add_result(_result("a", "text", 0.9))
    agg.add_result(_result("b", "text", 0.4))
    out = agg.get_weighted_result("task-1")
    assert out.strategy == AggregationStrategy.BEST_CONFIDENCE
    assert out.consensus_value == "text"


def test_weighted_average_zero_total_weight_falls_back() -> None:
    agg = ResultAggregator()
    agg.add_result(_result("a", 5, 0.0))
    agg.add_result(_result("b", 9, 0.0))
    out = agg.get_weighted_result("task-1")
    assert out.strategy == AggregationStrategy.BEST_CONFIDENCE
    assert out.consensus_value == 5


def test_best_confidence_default_strategy() -> None:
    agg = ResultAggregator(consensus_threshold=0.6)
    agg.add_result(_result("a", "low", 0.3))
    agg.add_result(_result("b", "high", 0.95))
    out = agg.aggregate("task-1")
    assert out.strategy == AggregationStrategy.BEST_CONFIDENCE
    assert out.consensus_value == "high"
    assert out.consensus_reached is True
    assert out.divergent_agents == ["a"]


def test_best_confidence_below_threshold() -> None:
    agg = ResultAggregator(consensus_threshold=0.99)
    agg.add_result(_result("a", "only", 0.4))
    out = agg.aggregate("task-1", strategy=AggregationStrategy.BEST_CONFIDENCE)
    assert out.consensus_reached is False


def test_aggregate_unknown_strategy_hits_else() -> None:
    agg = ResultAggregator()
    agg.add_result(_result("a", "x", 0.9))
    out = agg.aggregate("task-1", strategy="not-a-strategy")  # type: ignore[arg-type]
    assert out.strategy == AggregationStrategy.BEST_CONFIDENCE
    assert out.consensus_value == "x"


def test_get_divergence_variants() -> None:
    agg = ResultAggregator()

    # fewer than two results
    agg.add_result(_result("a", "x", 0.9))
    assert agg.get_divergence("task-1") == []

    # no consensus -> all results returned
    agg.add_result(_result("b", "y", 0.9))
    agg.add_result(_result("c", "z", 0.9))
    no_consensus = ResultAggregator(consensus_threshold=0.99)
    r1 = _result("a", "x", 0.9)
    r2 = _result("b", "y", 0.9)
    no_consensus.add_result(r1)
    no_consensus.add_result(r2)
    assert no_consensus.get_divergence("task-1") == [r1, r2]

    # consensus -> only divergent agents
    consensus = ResultAggregator(consensus_threshold=0.6)
    consensus.add_result(_result("a", "same", 0.9))
    consensus.add_result(_result("b", "same", 0.9))
    consensus.add_result(_result("c", "diff", 0.9))
    divergent = consensus.get_divergence("task-1")
    assert [d.agent_id for d in divergent] == ["c"]


def test_history_and_clear() -> None:
    agg = ResultAggregator()
    agg.add_result(_result("a", "x", 0.9, task_id="t1"))
    agg.add_result(_result("b", "y", 0.9, task_id="t2"))
    agg.aggregate("t1")
    agg.aggregate("t2")
    assert len(agg.get_history()) == 2
    assert len(agg.get_history("t1")) == 1
    assert agg.get_history("nope") == []

    agg.clear_task("t1")
    assert agg.get_results("t1") == []

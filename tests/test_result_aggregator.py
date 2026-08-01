"""Tests for result aggregation and cross-validation."""

from __future__ import annotations

from app.multi_agent.result_aggregator import AgentResult, ResultAggregator, get_aggregator


class TestResultAggregator:
    def test_single_result(self) -> None:
        agg = ResultAggregator()
        result = AgentResult(
            agent_name="executor",
            task_description="read file",
            output="File content here",
        )
        out = agg.aggregate("test", [result])
        assert out.confidence == 1.0
        assert out.needs_review is False
        assert out.consensus == "File content here"

    def test_empty_results(self) -> None:
        agg = ResultAggregator()
        out = agg.aggregate("test", [])
        assert out.confidence == 0.0
        assert out.needs_review is True

    def test_all_failed(self) -> None:
        agg = ResultAggregator()
        results = [
            AgentResult(agent_name="a", task_description="t", output="", success=False, error="timeout"),
            AgentResult(agent_name="b", task_description="t", output="", success=False, error="crash"),
        ]
        out = agg.aggregate("test", results)
        assert out.needs_review is True
        assert "All agents failed" in out.discrepancies

    def test_consistent_outputs(self) -> None:
        agg = ResultAggregator()
        results = [
            AgentResult(agent_name="a", task_description="t", output="same result"),
            AgentResult(agent_name="b", task_description="t", output="same result"),
        ]
        out = agg.aggregate("test", results)
        assert out.confidence == 1.0
        assert not out.discrepancies
        assert out.needs_review is False

    def test_divergent_outputs(self) -> None:
        agg = ResultAggregator()
        results = [
            AgentResult(agent_name="a", task_description="t", output="Option A is correct"),
            AgentResult(agent_name="b", task_description="t", output="Option B is correct"),
        ]
        out = agg.aggregate("test", results)
        assert out.discrepancies
        assert out.needs_review is True
        assert out.confidence < 1.0

    def test_partial_failure(self) -> None:
        agg = ResultAggregator()
        results = [
            AgentResult(agent_name="a", task_description="t", output="success"),
            AgentResult(agent_name="b", task_description="t", output="", success=False, error="timeout"),
        ]
        out = agg.aggregate("test", results)
        assert out.needs_review is True
        assert any("Partial failure" in d for d in out.discrepancies)

    def test_consensus_multiple_success(self) -> None:
        agg = ResultAggregator()
        results = [
            AgentResult(agent_name="a", task_description="t", output="result A"),
            AgentResult(agent_name="b", task_description="t", output="result B"),
        ]
        out = agg.aggregate("test", results)
        assert "a" in out.consensus
        assert "b" in out.consensus

    def test_singleton(self) -> None:
        a = get_aggregator()
        b = get_aggregator()
        assert a is b


class TestAgentResult:
    def test_defaults(self) -> None:
        r = AgentResult(agent_name="x", task_description="y", output="z")
        assert r.success is True
        assert r.error == ""
        assert r.metadata == {}

"""Tests for the reasoning engine: data models, components, strategies, pipeline, and API.

Covers Phase 1 (Tree of Thoughts + Self-Refine + Coverage) end-to-end with mock LLM.
"""

from __future__ import annotations

import asyncio
import json
import os
import pytest
import pytest_asyncio

os.environ["APP_TESTING"] = "true"

from app.core.reasoning.base import (
    Assumption,
    Candidate,
    CoverageReport,
    CritiqueResult,
    EdgeCase,
    Issue,
    IssueSeverity,
    PathTrace,
    ReasoningMode,
    ReasoningRequest,
    ReasoningResult,
    ReasoningTrace,
    Risk,
    RoundTrace,
    Strategy,
)
from app.core.reasoning.components.coverage import CoverageChecker
from app.core.reasoning.components.reflection_memory import ReflectionMemory, ReflectionEntry
from app.core.reasoning.components.scorer import CandidateScorer, _DEFAULT_WEIGHTS
from app.core.reasoning.components.self_refine import SelfRefineLoop, _parse_critique_response
from app.core.reasoning.components.trace import ReasoningTracer
from app.core.reasoning.pipeline import ReasoningPipeline
from app.core.reasoning.selector import StrategySelector
from app.core.reasoning.strategies.tree_of_thought import TreeOfThoughtStrategy
from app.core.reasoning.strategies.deep_refine import DeepRefineStrategy, Snapshot
from app.core.reasoning.strategies.debate import DebateStrategy


# ─── Mock Model Adapter ───────────────────────────────────────────────────

class MockModelResponse:
    def __init__(self, content: str):
        self.content = content
        self.usage = {"prompt_tokens": 100, "completion_tokens": 50}


class MockModelAdapter:
    """Mock LLM adapter that returns controlled responses."""

    def __init__(self, responses: list[str] | None = None):
        self._responses = responses or []
        self._call_count = 0
        self.provider = "mock"

    async def chat(self, messages, **kwargs):
        idx = min(self._call_count, len(self._responses) - 1)
        content = self._responses[idx] if self._responses else '{"passed": true, "issues": [], "scores": {"correctness": 5, "completeness": 5, "clarity": 5, "safety": 5, "actionability": 5}}'
        self._call_count += 1
        return MockModelResponse(content)

    async def stream_chat(self, messages, **kwargs):
        idx = min(self._call_count, len(self._responses) - 1)
        content = self._responses[idx] if self._responses else "This is a mock response for testing purposes."
        self._call_count += 1
        for char in content:
            yield MockModelResponse(char)


class MockModelRegistry:
    def __init__(self, adapter):
        self._adapter = adapter

    def get_or_create(self, model_name: str):
        return self._adapter

    def get_default(self):
        return self._adapter


# ═══════════════════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════════════════

class TestDataModel:
    """Tests for reasoning data models."""

    def test_issue_creation(self):
        issue = Issue(
            severity=IssueSeverity.CRITICAL,
            description="SQL injection vulnerability in user query",
            location="db.py:42",
            fix_suggestion="Use parameterized queries",
        )
        assert issue.severity == IssueSeverity.CRITICAL
        assert issue.location == "db.py:42"

    def test_issue_min_length(self):
        with pytest.raises(Exception):
            Issue(severity=IssueSeverity.MAJOR, description="short")

    def test_critique_result_properties(self):
        critique = CritiqueResult(
            passed=False,
            issues=[
                Issue(severity=IssueSeverity.CRITICAL, description="Critical issue in auth flow"),
                Issue(severity=IssueSeverity.MAJOR, description="Major issue in validation"),
                Issue(severity=IssueSeverity.MAJOR, description="Another major issue"),
                Issue(severity=IssueSeverity.MINOR, description="Minor formatting issue"),
            ],
            scores={"correctness": 2.0, "completeness": 3.0, "clarity": 4.0, "safety": 1.0, "actionability": 3.0},
        )
        assert critique.critical_count == 1
        assert critique.major_count == 2
        assert critique.average_score == 2.6

    def test_critique_result_average_empty(self):
        critique = CritiqueResult(scores={})
        assert critique.average_score == 0.0

    def test_critique_feedback_string(self):
        critique = CritiqueResult(
            passed=False,
            summary="Needs improvement",
            issues=[
                Issue(severity=IssueSeverity.CRITICAL, description="Critical issue"),
            ],
        )
        feedback = critique.to_feedback_string()
        assert "Needs improvement" in feedback
        assert "CRITICAL" in feedback
        assert "Critical issue" in feedback

    def test_critique_feedback_string_empty_when_passed(self):
        critique = CritiqueResult(passed=True, issues=[])
        assert critique.to_feedback_string() == ""

    def test_candidate_creation(self):
        candidate = Candidate(
            strategy="tree_of_thought",
            path_type="analytical",
            content="Test content",
            confidence=0.85,
        )
        assert len(candidate.id) == 8
        assert candidate.strategy == "tree_of_thought"

    def test_edge_case(self):
        edge = EdgeCase(description="Empty input", category="boundary", tested=True, result="handled")
        assert edge.tested is True

    def test_risk_score(self):
        risk = Risk(description="Data loss", probability="high", impact="high")
        assert risk.risk_score == 9

    def test_risk_score_low(self):
        risk = Risk(description="Minor bug", probability="low", impact="low")
        assert risk.risk_score == 1

    def test_coverage_report_properties(self):
        coverage = CoverageReport(
            risks=[
                Risk(description="r1", probability="high", impact="high"),
                Risk(description="r2", probability="low", impact="low"),
            ],
            assumptions=[
                Assumption(statement="User has internet", validated=False),
                Assumption(statement="API is available", validated=True),
            ],
        )
        assert len(coverage.high_risks) == 1
        assert len(coverage.unvalidated_assumptions) == 1

    def test_coverage_summary(self):
        coverage = CoverageReport(
            score=0.85,
            edge_cases=[EdgeCase(description="e1", category="c", tested=True)],
            blind_spots=["spot1"],
        )
        summary = coverage.summary()
        assert "85%" in summary
        assert "1/1 tested" in summary

    def test_reasoning_request_defaults(self):
        request = ReasoningRequest(task="Test task")
        assert request.mode == ReasoningMode.AUTO
        assert request.max_paths == 3
        assert request.coverage_enabled is True

    def test_reasoning_request_custom(self):
        request = ReasoningRequest(
            task="Code something",
            mode=ReasoningMode.TREE_OF_THOUGHT,
            max_paths=5,
            max_refine_rounds=2,
        )
        assert request.max_paths == 5
        assert request.max_refine_rounds == 2

    def test_reasoning_request_bounds(self):
        with pytest.raises(Exception):
            ReasoningRequest(task="Test", max_paths=0)
        with pytest.raises(Exception):
            ReasoningRequest(task="Test", max_paths=6)

    def test_reasoning_trace(self):
        trace = ReasoningTrace(request_task="test", strategy_selected="tree")
        assert len(trace.trace_id) == 12
        assert trace.path_traces == []

    def test_strategy_protocol(self):
        assert hasattr(Strategy, "execute")
        # Protocol class vars are defined on implementations, not the Protocol itself
        strategy = TreeOfThoughtStrategy()
        assert hasattr(strategy, "name")
        assert strategy.name == "tree_of_thought"


# ═══════════════════════════════════════════════════════════════════════════
# Strategy Selector
# ═══════════════════════════════════════════════════════════════════════════

class TestStrategySelector:
    def test_auto_mode_with_tree_available(self):
        selector = StrategySelector()
        request = ReasoningRequest(task="design a system", mode=ReasoningMode.AUTO)
        available = {ReasoningMode.TREE_OF_THOUGHT: object()}
        result = selector.select(request, available)
        assert result == ReasoningMode.TREE_OF_THOUGHT

    def test_explicit_mode_respected(self):
        selector = StrategySelector()
        request = ReasoningRequest(task="test", mode=ReasoningMode.DEEP_REFINE)
        available = {
            ReasoningMode.DEEP_REFINE: object(),
            ReasoningMode.TREE_OF_THOUGHT: object(),
        }
        result = selector.select(request, available)
        assert result == ReasoningMode.DEEP_REFINE

    def test_explicit_mode_fallback(self):
        selector = StrategySelector()
        request = ReasoningRequest(task="test", mode=ReasoningMode.DEBATE)
        available = {ReasoningMode.TREE_OF_THOUGHT: object()}
        result = selector.select(request, available)
        assert result == ReasoningMode.TREE_OF_THOUGHT

    def test_coding_keyword_no_deep(self):
        selector = StrategySelector()
        request = ReasoningRequest(task="implement a function", mode=ReasoningMode.AUTO)
        available = {ReasoningMode.TREE_OF_THOUGHT: object()}
        result = selector.select(request, available)
        assert result == ReasoningMode.TREE_OF_THOUGHT

    def test_eval_keyword_no_debate(self):
        selector = StrategySelector()
        request = ReasoningRequest(task="evaluate this approach", mode=ReasoningMode.AUTO)
        available = {ReasoningMode.TREE_OF_THOUGHT: object()}
        result = selector.select(request, available)
        assert result == ReasoningMode.TREE_OF_THOUGHT


# ═══════════════════════════════════════════════════════════════════════════
# Self-Refine Loop
# ═══════════════════════════════════════════════════════════════════════════

class TestSelfRefineLoop:
    @pytest.mark.asyncio
    async def test_refine_passes_first_round(self):
        critique_json = json.dumps({
            "passed": True,
            "summary": "Good output",
            "scores": {"correctness": 5, "completeness": 5, "clarity": 5, "safety": 5, "actionability": 5},
            "issues": [],
        })
        adapter = MockModelAdapter(responses=[critique_json])
        loop = SelfRefineLoop()
        content, critique, traces = await loop.refine(
            task="Write a hello world function",
            initial="def hello(): return 'world'",
            model_adapter=adapter,
            max_rounds=3,
        )
        assert critique.passed is True
        assert len(traces) >= 1
        assert traces[0].action == "critique"

    @pytest.mark.asyncio
    async def test_refine_with_improvement(self):
        critique1 = json.dumps({
            "passed": False,
            "summary": "Needs error handling",
            "scores": {"correctness": 3, "completeness": 2, "clarity": 4, "safety": 5, "actionability": 3},
            "issues": [
                {"severity": "major", "description": "Missing error handling for edge cases"},
            ],
        })
        critique2 = json.dumps({
            "passed": True,
            "summary": "Good output",
            "scores": {"correctness": 5, "completeness": 5, "clarity": 5, "safety": 5, "actionability": 5},
            "issues": [],
        })
        adapter = MockModelAdapter(responses=[critique1, "def hello(): return 'world'", critique2])
        loop = SelfRefineLoop()
        content, critique, traces = await loop.refine(
            task="Write a hello world function",
            initial="def hello(): return 'world'",
            model_adapter=adapter,
            max_rounds=3,
        )
        assert critique.passed is True
        assert len(traces) >= 2

    @pytest.mark.asyncio
    async def test_refine_max_rounds_reached(self):
        critique_fail = json.dumps({
            "passed": False,
            "summary": "Still has issues",
            "scores": {"correctness": 2, "completeness": 2, "clarity": 2, "safety": 2, "actionability": 2},
            "issues": [
                {"severity": "major", "description": "Issue still present"},
            ],
        })
        adapter = MockModelAdapter(responses=[critique_fail] * 6)
        loop = SelfRefineLoop()
        content, critique, traces = await loop.refine(
            task="Test task",
            initial="Initial content",
            model_adapter=adapter,
            max_rounds=3,
        )
        assert critique.passed is False

    def test_parse_valid_critique(self):
        raw = json.dumps({
            "passed": True,
            "summary": "Good",
            "scores": {"correctness": 5, "completeness": 4, "clarity": 5, "safety": 5, "actionability": 4},
            "issues": [],
        })
        result = _parse_critique_response(raw)
        assert result.passed is True
        assert result.scores["correctness"] == 5.0

    def test_parse_critique_with_code_block(self):
        raw = '```json\n{"passed": false, "scores": {"correctness": 3}, "issues": []}\n```'
        result = _parse_critique_response(raw)
        assert result.passed is False
        assert "correctness" in result.scores

    def test_parse_critique_invalid_json(self):
        raw = "This is not JSON at all"
        result = _parse_critique_response(raw)
        assert result.passed is False
        assert "Failed to parse" in result.summary


# ═══════════════════════════════════════════════════════════════════════════
# Coverage Checker
# ═══════════════════════════════════════════════════════════════════════════

class TestCoverageChecker:
    @pytest.mark.asyncio
    async def test_check_with_candidates(self):
        coverage_json = json.dumps({
            "edge_cases": [
                {"description": "Empty input", "category": "boundary"},
                {"description": "Very large input", "category": "boundary"},
            ],
            "risks": [
                {"description": "Data corruption", "probability": "low", "impact": "high"},
            ],
            "assumptions": [
                {"statement": "Input is UTF-8 encoded"},
            ],
            "blind_spots": ["Performance under concurrent load"],
        })
        adapter = MockModelAdapter(responses=[coverage_json])
        checker = CoverageChecker()
        candidates = [
            Candidate(strategy="tree", path_type="analytical", content="Solution A", confidence=0.8),
            Candidate(strategy="tree", path_type="code_first", content="Solution B", confidence=0.7),
        ]
        report = await checker.check("Write a function", candidates, adapter, "general")
        assert len(report.edge_cases) >= 2
        assert len(report.risks) >= 1
        assert len(report.assumptions) >= 1
        assert 0.0 <= report.score <= 1.0

    @pytest.mark.asyncio
    async def test_check_with_fallback(self):
        adapter = MockModelAdapter(responses=["invalid response"])
        checker = CoverageChecker()
        candidates = [
            Candidate(strategy="tree", path_type="analytical", content="A solution", confidence=0.7),
        ]
        report = await checker.check("Test task", candidates, adapter, "code")
        assert report.score >= 0.0
        assert isinstance(report.checklist, dict)


# ═══════════════════════════════════════════════════════════════════════════
# Candidate Scorer
# ═══════════════════════════════════════════════════════════════════════════

class TestCandidateScorer:
    def test_select_best_single(self):
        scorer = CandidateScorer()
        candidate = Candidate(id="c1", content="test", confidence=0.8)
        best = scorer.select_best([candidate])
        assert best.id == "c1"

    def test_select_best_multiple(self):
        scorer = CandidateScorer()
        c1 = Candidate(
            id="c1",
            content="lower score",
            confidence=0.5,
            critique=CritiqueResult(
                passed=False,
                scores={"correctness": 2, "completeness": 2, "clarity": 2, "safety": 2, "actionability": 2},
            ),
        )
        c2 = Candidate(
            id="c2",
            content="higher score",
            confidence=0.9,
            critique=CritiqueResult(
                passed=True,
                scores={"correctness": 5, "completeness": 5, "clarity": 5, "safety": 5, "actionability": 5},
            ),
        )
        best = scorer.select_best([c1, c2])
        assert best.id == "c2"

    def test_select_best_empty_raises(self):
        scorer = CandidateScorer()
        with pytest.raises(ValueError):
            scorer.select_best([])

    def test_weights_validation(self):
        scorer = CandidateScorer(weights={"correctness": 1.0, "completeness": 1.0})
        total = sum(scorer.weights.values())
        assert abs(total - 1.0) < 0.01

    def test_weighted_score_normalization(self):
        scorer = CandidateScorer()
        scores = {"correctness": 5.0, "completeness": 4.0, "clarity": 3.0, "safety": 5.0, "actionability": 4.0}
        result = scorer._weighted_score(scores)
        assert 0.0 <= result <= 1.0

    def test_critical_penalty(self):
        scorer = CandidateScorer()
        base = 0.8
        critique = CritiqueResult(
            passed=False,
            critical_count=2,
            issues=[
                Issue(severity=IssueSeverity.CRITICAL, description="Critical issue one"),
                Issue(severity=IssueSeverity.CRITICAL, description="Critical issue two"),
            ],
        )
        adjusted = scorer._apply_modifiers(base, critique)
        assert adjusted < base

    def test_coverage_integration(self):
        scorer = CandidateScorer()
        coverage = CoverageReport(score=0.9)
        c1 = Candidate(
            id="c1",
            content="test",
            confidence=0.5,
            critique=CritiqueResult(
                passed=False,
                scores={"correctness": 2, "completeness": 2, "clarity": 2, "safety": 2, "actionability": 2},
            ),
        )
        c2 = Candidate(
            id="c2",
            content="test",
            confidence=0.6,
            critique=CritiqueResult(
                passed=True,
                scores={"correctness": 4, "completeness": 4, "clarity": 4, "safety": 4, "actionability": 4},
            ),
        )
        best = scorer.select_best([c1, c2], coverage)
        assert best.id == "c2"


# ═══════════════════════════════════════════════════════════════════════════
# Reasoning Tracer
# ═══════════════════════════════════════════════════════════════════════════

class TestReasoningTracer:
    def test_start_and_finish(self):
        tracer = ReasoningTracer()
        tracer.start("test task", ReasoningMode.TREE_OF_THOUGHT)
        trace = tracer.finish()
        assert trace.request_task == "test task"
        assert trace.strategy_selected == "tree"
        assert trace.total_duration_ms >= 0

    def test_record_path_lifecycle(self):
        tracer = ReasoningTracer()
        tracer.start("test", ReasoningMode.TREE_OF_THOUGHT)
        tracer.record_path_start("analytical", "p0_ana")
        tracer.record_path_end("p0_ana", 0.85)
        trace = tracer.finish()
        assert len(trace.path_traces) == 1
        assert trace.path_traces[0].path_type == "analytical"
        assert trace.path_traces[0].final_confidence == 0.85

    def test_record_round(self):
        tracer = ReasoningTracer()
        tracer.start("test", ReasoningMode.TREE_OF_THOUGHT)
        tracer.record_path_start("analytical", "p0_ana")
        tracer.record_round("p0_ana", RoundTrace(round_num=1, action="critique"))
        trace = tracer.finish()
        assert len(trace.path_traces[0].rounds) == 1

    def test_record_coverage(self):
        tracer = ReasoningTracer()
        tracer.start("test", ReasoningMode.TREE_OF_THOUGHT)
        coverage = CoverageReport(score=0.85)
        tracer.record_coverage(coverage)
        trace = tracer.finish()
        assert len(trace.coverage_checks) == 1
        assert trace.coverage_checks[0]["score"] == 0.85

    def test_record_selection(self):
        tracer = ReasoningTracer()
        tracer.start("test", ReasoningMode.TREE_OF_THOUGHT)
        tracer.record_selection("Selected c1 (best score)")
        trace = tracer.finish()
        assert "Selected c1" in trace.final_selection_reason

    def test_snapshot_isolation(self):
        tracer = ReasoningTracer()
        tracer.start("test", ReasoningMode.TREE_OF_THOUGHT)
        snapshot = tracer.snapshot()
        tracer.record_path_start("analytical", "p0_ana")
        assert len(snapshot.path_traces) == 0

    @pytest.mark.asyncio
    async def test_thread_safety(self):
        tracer = ReasoningTracer()
        tracer.start("test", ReasoningMode.TREE_OF_THOUGHT)

        async def record_paths():
            for i in range(10):
                tracer.record_path_start(f"path_{i}", f"p{i}")
                tracer.record_path_end(f"p{i}", 0.5 + i * 0.01)

        await record_paths()
        trace = tracer.finish()
        assert len(trace.path_traces) == 10


# ═══════════════════════════════════════════════════════════════════════════
# Reasoning Pipeline
# ═══════════════════════════════════════════════════════════════════════════

class TestReasoningPipeline:
    @pytest.mark.asyncio
    async def test_pipeline_register_strategy(self):
        pipeline = ReasoningPipeline()
        strategy = TreeOfThoughtStrategy()
        pipeline.register_strategy(ReasoningMode.TREE_OF_THOUGHT, strategy)
        assert ReasoningMode.TREE_OF_THOUGHT in pipeline._strategies

    @pytest.mark.asyncio
    async def test_pipeline_reason_with_mocked_adapter(self):
        critique_json = json.dumps({
            "passed": True,
            "summary": "Good",
            "scores": {"correctness": 5, "completeness": 5, "clarity": 5, "safety": 5, "actionability": 5},
            "issues": [],
        })
        coverage_json = json.dumps({
            "edge_cases": [{"description": "Empty input", "category": "boundary"}],
            "risks": [],
            "assumptions": [],
            "blind_spots": [],
        })
        responses = [critique_json] * 20 + [coverage_json] * 5
        adapter = MockModelAdapter(responses=responses)
        registry = MockModelRegistry(adapter)

        pipeline = ReasoningPipeline(model_registry=registry)
        strategy = TreeOfThoughtStrategy()
        pipeline.register_strategy(ReasoningMode.TREE_OF_THOUGHT, strategy)
        pipeline._selector = StrategySelector()

        request = ReasoningRequest(
            task="Write a Python function that adds two numbers",
            mode=ReasoningMode.TREE_OF_THOUGHT,
            max_paths=2,
            max_refine_rounds=1,
            coverage_enabled=True,
            model_override="mock-model",
        )

        result = await pipeline.reason(request)
        assert isinstance(result, ReasoningResult)
        assert result.mode_used == ReasoningMode.TREE_OF_THOUGHT
        assert len(result.candidates) >= 1
        assert result.total_duration_ms > 0
        assert result.trace is not None

    @pytest.mark.asyncio
    async def test_pipeline_auto_mode_selection(self):
        critique_json = json.dumps({
            "passed": True,
            "scores": {"correctness": 5, "completeness": 5, "clarity": 5, "safety": 5, "actionability": 5},
            "issues": [],
        })
        coverage_json = json.dumps({
            "edge_cases": [],
            "risks": [],
            "assumptions": [],
            "blind_spots": [],
        })
        adapter = MockModelAdapter(responses=[critique_json] * 20 + [coverage_json] * 5)
        registry = MockModelRegistry(adapter)

        pipeline = ReasoningPipeline(model_registry=registry)
        strategy = TreeOfThoughtStrategy()
        pipeline.register_strategy(ReasoningMode.TREE_OF_THOUGHT, strategy)

        request = ReasoningRequest(
            task="design a microservices architecture",
            mode=ReasoningMode.AUTO,
            max_paths=1,
            max_refine_rounds=1,
            coverage_enabled=False,
        )

        result = await pipeline.reason(request)
        assert isinstance(result, ReasoningResult)
        assert result.mode_used == ReasoningMode.TREE_OF_THOUGHT

    @pytest.mark.asyncio
    async def test_pipeline_no_candidates_error_handling(self):
        """Test that pipeline handles empty candidate list gracefully."""
        pipeline = ReasoningPipeline()
        strategy = TreeOfThoughtStrategy()
        pipeline.register_strategy(ReasoningMode.TREE_OF_THOUGHT, strategy)

        async def mock_execute(*args, **kwargs):
            return []

        strategy.execute = mock_execute

        request = ReasoningRequest(
            task="Test",
            mode=ReasoningMode.TREE_OF_THOUGHT,
            max_paths=1,
            max_refine_rounds=1,
            coverage_enabled=False,
        )

        result = await pipeline.reason(request)
        assert "No valid candidates" in result.answer


# ═══════════════════════════════════════════════════════════════════════════
# Tree of Thought Strategy
# ═══════════════════════════════════════════════════════════════════════════

class TestTreeOfThoughtStrategy:
    @pytest.mark.asyncio
    async def test_strategy_generates_candidates(self):
        critique_json = json.dumps({
            "passed": True,
            "scores": {"correctness": 5, "completeness": 5, "clarity": 5, "safety": 5, "actionability": 5},
            "issues": [],
        })
        adapter = MockModelAdapter(responses=[critique_json] * 20)
        registry = MockModelRegistry(adapter)

        strategy = TreeOfThoughtStrategy()
        request = ReasoningRequest(
            task="Explain Python decorators",
            max_paths=3,
            max_refine_rounds=1,
            model_override="mock",
        )

        self_refine = SelfRefineLoop()
        candidates = await strategy.execute(request, self_refine, registry)
        assert len(candidates) == 3
        for c in candidates:
            assert isinstance(c, Candidate)
            assert c.strategy == "tree_of_thought"
            assert len(c.path_type) > 0

    @pytest.mark.asyncio
    async def test_path_types_selection(self):
        strategy = TreeOfThoughtStrategy()
        types = strategy._select_path_types(3)
        assert len(types) == 3
        assert types == ["analytical", "code_first", "research"]

    @pytest.mark.asyncio
    async def test_path_types_five(self):
        strategy = TreeOfThoughtStrategy()
        types = strategy._select_path_types(5)
        assert len(types) == 5
        assert "contrarian" in types
        assert "pragmatic" in types


# ═══════════════════════════════════════════════════════════════════════════
# API Endpoints
# ═══════════════════════════════════════════════════════════════════════════

class TestReasoningAPI:
    @pytest.mark.asyncio
    async def test_list_modes_auth_required(self, client):
        response = await client.get("/api/v1/reason/modes")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_reason_endpoint_auth_required(self, client):
        request_data = {
            "task": "Test task",
            "mode": "tree",
            "max_paths": 1,
            "max_refine_rounds": 1,
        }
        response = await client.post("/api/v1/reason", json=request_data)
        assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# Reflection Memory (Phase 2)
# ═══════════════════════════════════════════════════════════════════════════

class TestReflectionMemory:
    def test_add_and_retrieve(self):
        mem = ReflectionMemory()
        mem.add_reflection(1, "missing error handling", "Always validate inputs", "Add input validation")
        assert mem.size == 1

    def test_generate_guidance(self):
        mem = ReflectionMemory()
        mem.add_reflection(1, "missing error handling", "Always validate inputs", "Add input validation")
        guidance = mem.generate_guidance()
        assert "Lessons from Previous Attempts" in guidance
        assert "missing error handling" in guidance
        assert "Always validate inputs" in guidance

    def test_max_entries(self):
        mem = ReflectionMemory(max_entries=3)
        for i in range(5):
            mem.add_reflection(i, f"reason_{i}", f"lesson_{i}", f"approach_{i}")
        assert mem.size == 3

    def test_get_failure_patterns(self):
        mem = ReflectionMemory()
        mem.add_reflection(1, "syntax error", "Check syntax", "Use linter")
        mem.add_reflection(2, "logic error", "Test edge cases", "Add tests")
        patterns = mem.get_failure_patterns()
        assert len(patterns) == 2
        assert "syntax error" in patterns

    def test_clear(self):
        mem = ReflectionMemory()
        mem.add_reflection(1, "reason", "lesson", "approach")
        mem.clear()
        assert mem.size == 0

    def test_guidance_empty_when_no_entries(self):
        mem = ReflectionMemory()
        assert mem.generate_guidance() == ""


# ═══════════════════════════════════════════════════════════════════════════
# DeepRefineStrategy (Phase 2)
# ═══════════════════════════════════════════════════════════════════════════

class TestDeepRefineStrategy:
    @pytest.mark.asyncio
    async def test_strategy_generates_candidate(self):
        critique_json = json.dumps({
            "passed": True,
            "scores": {"correctness": 5, "completeness": 5, "clarity": 5, "safety": 5, "actionability": 5},
            "issues": [],
        })
        adapter = MockModelAdapter(responses=[critique_json] * 20)
        registry = MockModelRegistry(adapter)

        strategy = DeepRefineStrategy()
        request = ReasoningRequest(
            task="Write a function to sort a list",
            mode=ReasoningMode.DEEP_REFINE,
            max_refine_rounds=1,
            model_override="mock",
        )

        candidates = await strategy.execute(request, SelfRefineLoop(), registry)
        assert len(candidates) == 1
        assert candidates[0].strategy == "deep_refine"
        assert candidates[0].path_type == "deep_refinement"

    @pytest.mark.asyncio
    async def test_strategy_with_reflection(self):
        critique1 = json.dumps({
            "passed": False,
            "summary": "Needs improvement",
            "scores": {"correctness": 3, "completeness": 2, "clarity": 4, "safety": 5, "actionability": 3},
            "issues": [{"severity": "major", "description": "Missing error handling for null inputs"}],
        })
        critique2 = json.dumps({
            "passed": True,
            "scores": {"correctness": 5, "completeness": 5, "clarity": 5, "safety": 5, "actionability": 5},
            "issues": [],
        })
        reflection_json = json.dumps({
            "failure_reason": "No error handling",
            "lesson": "Always validate inputs",
            "suggested_approach": "Add null checks at function entry",
        })
        backtrack_json = json.dumps({"decision": "continue", "reasoning": "Making progress"})
        adapter = MockModelAdapter(responses=[critique1, reflection_json, backtrack_json, critique2])
        registry = MockModelRegistry(adapter)

        strategy = DeepRefineStrategy()
        request = ReasoningRequest(
            task="Write robust code",
            mode=ReasoningMode.DEEP_REFINE,
            max_refine_rounds=3,
            model_override="mock",
        )

        candidates = await strategy.execute(request, SelfRefineLoop(), registry)
        assert len(candidates) == 1
        assert candidates[0].metadata["reflections"] >= 1

    def test_snapshot_creation(self):
        snapshot = Snapshot("test content", 0.8, 2, "Good progress")
        assert snapshot.content == "test content"
        assert snapshot.confidence == 0.8
        assert snapshot.round_num == 2

    def test_should_stop(self):
        strategy = DeepRefineStrategy()
        passing_critique = CritiqueResult(
            passed=True,
            scores={"correctness": 5, "completeness": 5, "clarity": 5, "safety": 5, "actionability": 5},
        )
        assert strategy._should_stop(passing_critique) is True

        failing_critique = CritiqueResult(
            passed=False,
            scores={"correctness": 2, "completeness": 2, "clarity": 2, "safety": 2, "actionability": 2},
        )
        assert strategy._should_stop(failing_critique) is False


# ═══════════════════════════════════════════════════════════════════════════
# DebateStrategy (Phase 3)
# ═══════════════════════════════════════════════════════════════════════════

class TestDebateStrategy:
    @pytest.mark.asyncio
    async def test_strategy_generates_candidate(self):
        judge_json = json.dumps({
            "converged": True,
            "winner": "synthesis",
            "reason": "Both sides reached agreement",
            "quality_score": 4,
            "final_solution": "The agreed solution",
        })
        adapter = MockModelAdapter(responses=[judge_json] * 10)
        registry = MockModelRegistry(adapter)

        strategy = DebateStrategy()
        request = ReasoningRequest(
            task="Evaluate microservices vs monolith",
            mode=ReasoningMode.DEBATE,
            max_refine_rounds=1,
            model_override="mock",
        )

        candidates = await strategy.execute(request, None, registry)
        assert len(candidates) == 1
        assert candidates[0].strategy == "debate"
        assert candidates[0].metadata["consensus_reached"] is True

    @pytest.mark.asyncio
    async def test_debate_max_rounds(self):
        judge_json = json.dumps({
            "converged": False,
            "winner": "proponent",
            "reason": "Still disagreeing",
            "quality_score": 3,
            "final_solution": "Best effort solution",
        })
        adapter = MockModelAdapter(responses=[judge_json] * 20)
        registry = MockModelRegistry(adapter)

        strategy = DebateStrategy()
        request = ReasoningRequest(
            task="Complex architectural decision",
            mode=ReasoningMode.DEBATE,
            max_refine_rounds=3,
            model_override="mock",
        )

        candidates = await strategy.execute(request, None, registry)
        assert len(candidates) == 1
        assert candidates[0].metadata["total_debate_rounds"] == 4

    @pytest.mark.asyncio
    async def test_debate_metadata(self):
        judge_json = json.dumps({
            "converged": True,
            "winner": "opponent",
            "reason": "Opponent had better arguments",
            "quality_score": 5,
            "final_solution": "Opponent solution wins",
        })
        adapter = MockModelAdapter(responses=[judge_json] * 5)
        registry = MockModelRegistry(adapter)

        strategy = DebateStrategy()
        request = ReasoningRequest(
            task="Test debate",
            mode=ReasoningMode.DEBATE,
            max_refine_rounds=1,
            model_override="mock",
        )
        candidates = await strategy.execute(request, None, registry)
        assert candidates[0].metadata["winner"] == "opponent"
        assert candidates[0].confidence >= 0.9


# ═══════════════════════════════════════════════════════════════════════════
# Integration: All strategies via pipeline
# ═══════════════════════════════════════════════════════════════════════════

class TestFullPipelineIntegration:
    @pytest.mark.asyncio
    async def test_deep_refine_via_pipeline(self):
        critique_json = json.dumps({
            "passed": True,
            "scores": {"correctness": 5, "completeness": 5, "clarity": 5, "safety": 5, "actionability": 5},
            "issues": [],
        })
        adapter = MockModelAdapter(responses=[critique_json] * 20)
        registry = MockModelRegistry(adapter)

        pipeline = ReasoningPipeline(model_registry=registry)
        pipeline.register_strategy(ReasoningMode.DEEP_REFINE, DeepRefineStrategy())
        pipeline.register_strategy(ReasoningMode.TREE_OF_THOUGHT, TreeOfThoughtStrategy())

        request = ReasoningRequest(
            task="Implement a binary search algorithm",
            mode=ReasoningMode.DEEP_REFINE,
            max_refine_rounds=1,
            coverage_enabled=False,
            model_override="mock",
        )

        result = await pipeline.reason(request)
        assert result.mode_used == ReasoningMode.DEEP_REFINE
        assert len(result.candidates) >= 1
        assert result.candidates[0].strategy == "deep_refine"

    @pytest.mark.asyncio
    async def test_debate_via_pipeline(self):
        judge_json = json.dumps({
            "converged": True,
            "winner": "synthesis",
            "reason": "Agreement reached",
            "quality_score": 4,
            "final_solution": "Agreed solution",
        })
        adapter = MockModelAdapter(responses=[judge_json] * 20)
        registry = MockModelRegistry(adapter)

        pipeline = ReasoningPipeline(model_registry=registry)
        pipeline.register_strategy(ReasoningMode.DEBATE, DebateStrategy())
        pipeline.register_strategy(ReasoningMode.TREE_OF_THOUGHT, TreeOfThoughtStrategy())

        request = ReasoningRequest(
            task="Choose between SQL and NoSQL",
            mode=ReasoningMode.DEBATE,
            max_refine_rounds=1,
            coverage_enabled=False,
            model_override="mock",
        )

        result = await pipeline.reason(request)
        assert result.mode_used == ReasoningMode.DEBATE
        assert len(result.candidates) >= 1
        assert result.candidates[0].strategy == "debate"

    @pytest.mark.asyncio
    async def test_selector_coding_to_deep_refine(self):
        selector = StrategySelector()
        request = ReasoningRequest(task="implement a function", mode=ReasoningMode.AUTO)
        available = {
            ReasoningMode.DEEP_REFINE: DeepRefineStrategy(),
            ReasoningMode.TREE_OF_THOUGHT: TreeOfThoughtStrategy(),
        }
        result = selector.select(request, available)
        assert result == ReasoningMode.DEEP_REFINE

    @pytest.mark.asyncio
    async def test_selector_eval_to_debate(self):
        selector = StrategySelector()
        request = ReasoningRequest(task="evaluate this architecture", mode=ReasoningMode.AUTO)
        available = {
            ReasoningMode.DEBATE: DebateStrategy(),
            ReasoningMode.TREE_OF_THOUGHT: TreeOfThoughtStrategy(),
        }
        result = selector.select(request, available)
        assert result == ReasoningMode.DEBATE

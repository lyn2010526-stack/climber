"""Tests for AGI P4 Observability Layer.

Covers: trace span creation and tree structure, decision audit chain
logging and retrieval, goal alignment scoring, emergency stop
activation/deactivation, and API endpoint authentication.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.core.observability.alignment import AlignmentCheck, Goal, GoalTracker
from app.core.observability.audit import AuditChain, AuditEntry
from app.core.observability.emergency_stop import EmergencyStopManager, EmergencyStopRecord
from app.core.observability.trace import TraceCollector, TraceSpan


# ---------------------------------------------------------------------------
# Trace Tests
# ---------------------------------------------------------------------------


class TestTraceSpan:
    def test_create_default(self):
        span = TraceSpan(operation="test_op")
        assert span.operation == "test_op"
        assert span.span_id != ""
        assert span.trace_id != ""
        assert span.status == "ok"
        assert span.parent_span_id == ""
        assert span.tags == {}
        assert span.events == []

    def test_create_with_parent(self):
        parent = TraceSpan(operation="parent_op")
        child = TraceSpan(operation="child_op", trace_id=parent.trace_id, parent_span_id=parent.span_id)
        assert child.trace_id == parent.trace_id
        assert child.parent_span_id == parent.span_id

    def test_to_dict(self):
        span = TraceSpan(operation="test", trace_id="t1", parent_span_id="p1")
        d = span.to_dict()
        assert d["operation"] == "test"
        assert d["trace_id"] == "t1"
        assert d["parent_span_id"] == "p1"
        assert "span_id" in d
        assert "started_at" in d


class TestTraceCollector:
    def test_start_span(self):
        collector = TraceCollector()
        span = collector.start_span(operation="test_op")
        assert span is not None
        assert span.operation == "test_op"
        assert span.span_id != ""
        collector.close()

    def test_start_span_sampled_out(self):
        collector = TraceCollector(sample_rate=0.0)
        span = collector.start_span(operation="test_op")
        assert span is None
        collector.close()

    def test_start_span_always_sampled(self):
        collector = TraceCollector(sample_rate=1.0)
        span = collector.start_span(operation="test_op")
        assert span is not None
        collector.close()

    def test_end_span(self):
        collector = TraceCollector()
        span = collector.start_span(operation="test_op")
        collector.end_span(span, status="ok")
        assert span.ended_at != ""
        assert span.status == "ok"
        collector.close()

    def test_add_event(self):
        collector = TraceCollector()
        span = collector.start_span(operation="test_op")
        collector.add_event(span, "checkpoint", {"step": 1})
        assert len(span.events) == 1
        assert span.events[0]["type"] == "checkpoint"
        assert span.events[0]["data"]["step"] == 1
        collector.close()

    def test_get_trace(self):
        collector = TraceCollector()
        root = collector.start_span(operation="root")
        child1 = collector.start_span(operation="child1", trace_id=root.trace_id, parent_span_id=root.span_id)
        child2 = collector.start_span(operation="child2", trace_id=root.trace_id, parent_span_id=root.span_id)
        collector.end_span(root)
        collector.end_span(child1)
        collector.end_span(child2)

        trace = collector.get_trace(root.trace_id)
        assert len(trace) == 3
        ops = {s.operation for s in trace}
        assert ops == {"root", "child1", "child2"}
        collector.close()

    def test_get_children(self):
        collector = TraceCollector()
        root = collector.start_span(operation="root")
        child1 = collector.start_span(operation="c1", trace_id=root.trace_id, parent_span_id=root.span_id)
        child2 = collector.start_span(operation="c2", trace_id=root.trace_id, parent_span_id=root.span_id)
        collector.end_span(root)
        collector.end_span(child1)
        collector.end_span(child2)

        children = collector.get_children(root.span_id)
        assert len(children) == 2
        collector.close()

    def test_list_traces(self):
        collector = TraceCollector()
        s1 = collector.start_span(operation="op1")
        s2 = collector.start_span(operation="op2")
        collector.end_span(s1)
        collector.end_span(s2)

        traces = collector.list_traces()
        assert len(traces) >= 2
        assert all("trace_id" in t for t in traces)
        assert all("span_count" in t for t in traces)
        collector.close()

    def test_get_span(self):
        collector = TraceCollector()
        span = collector.start_span(operation="test_op")
        collector.end_span(span)

        fetched = collector.get_span(span.span_id)
        assert fetched is not None
        assert fetched.span_id == span.span_id
        assert fetched.operation == "test_op"
        collector.close()

    def test_get_span_not_found(self):
        collector = TraceCollector()
        fetched = collector.get_span("nonexistent")
        assert fetched is None
        collector.close()

    def test_tree_structure(self):
        collector = TraceCollector()
        root = collector.start_span(operation="root")
        child = collector.start_span(operation="child", trace_id=root.trace_id, parent_span_id=root.span_id)
        grandchild = collector.start_span(operation="grandchild", trace_id=root.trace_id, parent_span_id=child.span_id)
        collector.end_span(root)
        collector.end_span(child)
        collector.end_span(grandchild)

        trace = collector.get_trace(root.trace_id)
        assert len(trace) == 3

        root_span = next(s for s in trace if s.operation == "root")
        child_span = next(s for s in trace if s.operation == "child")
        grandchild_span = next(s for s in trace if s.operation == "grandchild")

        assert root_span.parent_span_id == ""
        assert child_span.parent_span_id == root_span.span_id
        assert grandchild_span.parent_span_id == child_span.span_id
        collector.close()


# ---------------------------------------------------------------------------
# Audit Tests
# ---------------------------------------------------------------------------


class TestAuditEntry:
    def test_create_default(self):
        entry = AuditEntry(decision_type="routing")
        assert entry.decision_type == "routing"
        assert entry.id != ""
        assert entry.confidence == 0.0
        assert entry.alternatives_considered == []

    def test_to_dict(self):
        entry = AuditEntry(
            decision_type="tool_selection",
            input_summary="select tool",
            output_summary="chosen: search",
            rationale="best match",
            confidence=0.9,
            alternatives_considered=["browse", "code"],
        )
        d = entry.to_dict()
        assert d["decision_type"] == "tool_selection"
        assert d["confidence"] == 0.9
        assert d["alternatives_considered"] == ["browse", "code"]


class TestAuditChain:
    def test_log_decision(self):
        chain = AuditChain()
        entry = chain.log_decision(
            decision_type="routing",
            input_summary="user query",
            output_summary="route to agent-a",
            rationale="keyword match",
            confidence=0.85,
        )
        assert entry.id != ""
        assert entry.decision_type == "routing"
        assert entry.confidence == 0.85
        chain.close()

    def test_get_chain(self):
        chain = AuditChain()
        chain.log_decision(decision_type="routing", output_summary="r1")
        chain.log_decision(decision_type="tool_selection", output_summary="r2")
        chain.log_decision(decision_type="model_switch", output_summary="r3")

        entries = chain.get_chain()
        assert len(entries) == 3
        chain.close()

    def test_get_chain_pagination(self):
        chain = AuditChain()
        for i in range(5):
            chain.log_decision(decision_type="routing", output_summary=f"r{i}")

        entries = chain.get_chain(limit=2, offset=0)
        assert len(entries) == 2
        chain.close()

    def test_get_chain_by_session(self):
        chain = AuditChain()
        chain.log_decision(decision_type="routing", session_id="s1")
        chain.log_decision(decision_type="routing", session_id="s2")
        chain.log_decision(decision_type="routing", session_id="s1")

        entries = chain.get_chain(session_id="s1")
        assert len(entries) == 2
        chain.close()

    def test_search_by_type(self):
        chain = AuditChain()
        chain.log_decision(decision_type="routing")
        chain.log_decision(decision_type="tool_selection")
        chain.log_decision(decision_type="routing")

        entries = chain.search_by_type("routing")
        assert len(entries) == 2
        chain.close()

    def test_get_entry(self):
        chain = AuditChain()
        original = chain.log_decision(decision_type="routing", output_summary="test")
        fetched = chain.get_entry(original.id)
        assert fetched is not None
        assert fetched.id == original.id
        assert fetched.output_summary == "test"
        chain.close()

    def test_get_entry_not_found(self):
        chain = AuditChain()
        fetched = chain.get_entry("nonexistent")
        assert fetched is None
        chain.close()

    def test_export_chain(self):
        chain = AuditChain()
        chain.log_decision(decision_type="routing", output_summary="r1")
        chain.log_decision(decision_type="tool_selection", output_summary="r2")

        exported = chain.export_chain()
        import json
        data = json.loads(exported)
        assert len(data) == 2
        assert data[0]["decision_type"] in ("routing", "tool_selection")
        chain.close()

    def test_export_chain_filtered(self):
        chain = AuditChain()
        chain.log_decision(decision_type="routing", output_summary="r1")
        chain.log_decision(decision_type="tool_selection", output_summary="r2")

        exported = chain.export_chain(decision_type="routing")
        import json
        data = json.loads(exported)
        assert len(data) == 1
        assert data[0]["decision_type"] == "routing"
        chain.close()

    def test_count_entries(self):
        chain = AuditChain()
        assert chain.count_entries() == 0
        chain.log_decision(decision_type="routing")
        chain.log_decision(decision_type="tool_selection")
        assert chain.count_entries() == 2
        chain.close()

    def test_immutability_via_append_only(self):
        chain = AuditChain()
        entry = chain.log_decision(decision_type="routing", output_summary="original")
        entry.output_summary = "modified"
        fetched = chain.get_entry(entry.id)
        assert fetched is not None
        assert fetched.output_summary == "original"
        chain.close()


# ---------------------------------------------------------------------------
# Alignment Tests
# ---------------------------------------------------------------------------


class TestAlignmentCheck:
    def test_create_default(self):
        check = AlignmentCheck(goal_id="g1", current_action="search web")
        assert check.goal_id == "g1"
        assert check.current_action == "search web"
        assert check.alignment_score == 0.0
        assert check.notes == ""

    def test_to_dict(self):
        check = AlignmentCheck(
            goal_id="g1",
            current_action="search web",
            alignment_score=0.8,
            notes="aligned",
        )
        d = check.to_dict()
        assert d["alignment_score"] == 0.8
        assert d["notes"] == "aligned"


class TestGoalTracker:
    def test_register_goal(self):
        tracker = GoalTracker()
        goal = tracker.register_goal(
            description="Build a web scraper",
            keywords=["web", "scraper", "crawl"],
        )
        assert goal.id != ""
        assert goal.description == "Build a web scraper"
        assert goal.keywords == ["web", "scraper", "crawl"]
        assert goal.is_active is True
        tracker.close()

    def test_register_goal_auto_keywords(self):
        tracker = GoalTracker()
        goal = tracker.register_goal(description="Build a web scraper")
        assert len(goal.keywords) > 0
        tracker.close()

    def test_list_goals(self):
        tracker = GoalTracker()
        tracker.register_goal(description="Goal A", priority=2)
        tracker.register_goal(description="Goal B", priority=1)

        goals = tracker.list_goals()
        assert len(goals) == 2
        tracker.close()

    def test_deactivate_goal(self):
        tracker = GoalTracker()
        goal = tracker.register_goal(description="Goal A")
        assert tracker.deactivate_goal(goal.id) is True
        active = tracker.list_goals(active_only=True)
        assert len(active) == 0
        tracker.close()

    def test_check_alignment(self):
        tracker = GoalTracker()
        tracker.register_goal(
            description="Build a web scraper",
            keywords=["web", "scraper"],
        )
        checks = tracker.check_alignment("writing web scraper code")
        assert len(checks) == 1
        assert checks[0].alignment_score > 0
        tracker.close()

    def test_check_alignment_low_score(self):
        tracker = GoalTracker()
        tracker.register_goal(
            description="Build a web scraper",
            keywords=["web", "scraper"],
        )
        checks = tracker.check_alignment("cooking dinner recipes")
        assert len(checks) == 1
        assert checks[0].alignment_score < 0.5
        tracker.close()

    def test_is_aligned_true(self):
        tracker = GoalTracker(alignment_threshold=0.3)
        tracker.register_goal(
            description="Build a web scraper",
            keywords=["web", "scraper"],
        )
        assert tracker.is_aligned("writing web scraper code") is True
        tracker.close()

    def test_is_aligned_false(self):
        tracker = GoalTracker(alignment_threshold=0.9)
        tracker.register_goal(
            description="Build a web scraper",
            keywords=["web", "scraper"],
        )
        assert tracker.is_aligned("cooking dinner recipes") is False
        tracker.close()

    def test_get_drift_score(self):
        tracker = GoalTracker()
        tracker.register_goal(
            description="Build a web scraper",
            keywords=["web", "scraper"],
        )
        tracker.check_alignment("writing web scraper code")
        drift = tracker.get_drift_score()
        assert 0.0 <= drift <= 1.0
        tracker.close()

    def test_get_alignment_history(self):
        tracker = GoalTracker()
        tracker.register_goal(
            description="Build a web scraper",
            keywords=["web", "scraper"],
        )
        tracker.check_alignment("writing web scraper code")
        tracker.check_alignment("debugging scraper")

        history = tracker.get_alignment_history()
        assert len(history) == 2
        tracker.close()

    def test_get_goal(self):
        tracker = GoalTracker()
        goal = tracker.register_goal(description="Test goal")
        fetched = tracker.get_goal(goal.id)
        assert fetched is not None
        assert fetched.description == "Test goal"
        tracker.close()

    def test_get_goal_not_found(self):
        tracker = GoalTracker()
        fetched = tracker.get_goal("nonexistent")
        assert fetched is None
        tracker.close()


# ---------------------------------------------------------------------------
# Emergency Stop Tests
# ---------------------------------------------------------------------------


class TestEmergencyStopRecord:
    def test_create_default(self):
        record = EmergencyStopRecord(action="activate", triggered_by="user")
        assert record.action == "activate"
        assert record.triggered_by == "user"
        assert record.auto_trigger is False

    def test_to_dict(self):
        record = EmergencyStopRecord(action="deactivate", triggered_by="admin")
        d = record.to_dict()
        assert d["action"] == "deactivate"
        assert d["triggered_by"] == "admin"


class TestEmergencyStopManager:
    def test_initial_state(self):
        manager = EmergencyStopManager()
        assert manager.is_activated() is False
        status = manager.get_status()
        assert status["is_activated"] is False
        manager.close()

    def test_activate(self):
        manager = EmergencyStopManager()
        record = manager.activate(reason="test emergency", triggered_by="operator")
        assert manager.is_activated() is True
        assert record.action == "activate"
        assert record.reason == "test emergency"
        assert record.triggered_by == "operator"
        manager.close()

    def test_deactivate(self):
        manager = EmergencyStopManager()
        manager.activate(reason="test")
        record = manager.deactivate(reason="resolved", triggered_by="operator")
        assert manager.is_activated() is False
        assert record.action == "deactivate"
        assert record.reason == "resolved"
        manager.close()

    def test_get_status_after_activation(self):
        manager = EmergencyStopManager()
        manager.activate(reason="security breach", triggered_by="system")
        status = manager.get_status()
        assert status["is_activated"] is True
        assert status["reason"] == "security breach"
        assert status["activated_by"] == "system"
        assert status["activated_at"] != ""
        manager.close()

    def test_get_status_after_deactivation(self):
        manager = EmergencyStopManager()
        manager.activate(reason="test")
        manager.deactivate()
        status = manager.get_status()
        assert status["is_activated"] is False
        assert status["reason"] == ""
        manager.close()

    def test_get_log(self):
        manager = EmergencyStopManager()
        manager.activate(reason="first")
        manager.deactivate(reason="resolved")
        manager.activate(reason="second")

        log = manager.get_log()
        assert len(log) == 3
        assert log[0].action == "activate"
        assert log[1].action == "deactivate"
        manager.close()

    def test_auto_trigger_activates(self):
        manager = EmergencyStopManager(error_rate_threshold=0.5)
        record = manager.check_auto_trigger(recent_error_count=6, recent_total_count=10)
        assert record is not None
        assert manager.is_activated() is True
        assert record.auto_trigger is True
        manager.close()

    def test_auto_trigger_does_not_activate(self):
        manager = EmergencyStopManager(error_rate_threshold=0.5)
        record = manager.check_auto_trigger(recent_error_count=2, recent_total_count=10)
        assert record is None
        assert manager.is_activated() is False
        manager.close()

    def test_auto_trigger_no_data(self):
        manager = EmergencyStopManager(error_rate_threshold=0.5)
        record = manager.check_auto_trigger(recent_error_count=0, recent_total_count=0)
        assert record is None
        assert manager.is_activated() is False
        manager.close()

    def test_persistence_across_instances(self, tmp_path):
        db_path = str(tmp_path / "emergency_stop.db")
        manager = EmergencyStopManager(db_path=db_path)
        manager.activate(reason="persistent test", triggered_by="user")
        manager.close()

        manager2 = EmergencyStopManager(db_path=db_path)
        assert manager2.is_activated() is True
        status = manager2.get_status()
        assert status["reason"] == "persistent test"
        manager2.deactivate()
        manager2.close()


# ---------------------------------------------------------------------------
# API Endpoint Tests
# ---------------------------------------------------------------------------


class TestObservabilityAPI:
    """Test API endpoint authentication and basic responses."""

    @pytest.fixture
    def app(self):
        from fastapi import FastAPI
        from app.core.observability.api import router

        test_app = FastAPI()
        test_app.include_router(router)
        return test_app

    @pytest_asyncio.fixture
    async def client(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Auth removed for local-only mode")
    async def test_list_traces_requires_auth(self, client):
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Auth removed for local-only mode")
    async def test_get_trace_requires_auth(self, client):
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Auth removed for local-only mode")
    async def test_list_audit_requires_auth(self, client):
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Auth removed for local-only mode")
    async def test_alignment_requires_auth(self, client):
        pass

    @pytest.mark.skip(reason="Auth removed for local-only mode")
    @pytest.mark.asyncio
    async def test_emergency_stop_status_requires_auth(self, client):
        pass

    @pytest.mark.skip(reason="Auth removed for local-only mode")
    @pytest.mark.asyncio
    async def test_emergency_stop_activate_requires_auth(self, client):
        pass

    @pytest.mark.skip(reason="Auth removed for local-only mode")
    @pytest.mark.asyncio
    async def test_emergency_stop_deactivate_requires_auth(self, client):
        pass

    @pytest.mark.asyncio
    async def test_list_traces_with_auth(self, client):
        token = "test-user"
        response = await client.get(
            "/api/v1/observability/traces",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "traces" in data

    @pytest.mark.asyncio
    async def test_emergency_stop_with_auth(self, client):
        token = "test-user"

        response = await client.get(
            "/api/v1/observability/emergency-stop",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "is_activated" in data

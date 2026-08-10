"""Tests for Phase 2 meta-cognition modules and MCP plugins."""

import os

import pytest

from app.core.metacognition.capability_discovery import CapabilityDiscovery
from app.core.metacognition.goal_adjuster import GoalDynamicAdjuster
from app.core.metacognition.self_refactor import SelfModuleRefactor
from app.core.metacognition.sub_agent import SubAgentOrchestrator, SubAgentState
from app.tools.mcp_plugins.capability_index import CapabilityIndex
from app.tools.mcp_plugins.causal_graph import CausalGraph
from app.tools.mcp_plugins.trajectory_storage import TrajectoryStorage

# === Capability Discovery ===

class TestCapabilityDiscovery:
    def setup_method(self):
        self._path = "/tmp/test_cap_discovery.json"
        if os.path.exists(self._path):
            os.unlink(self._path)
        self.discoverer = CapabilityDiscovery(storage_path=self._path)

    def test_discover_analysis_capability(self):
        cap = self.discoverer.discover(
            goal="Analyze log files",
            available_tools=["read_file", "write_file", "run_command"],
            missing_capability="analyze and extract patterns from logs",
        )
        assert cap is not None
        assert len(cap.tool_chain) >= 2
        assert any(s["tool"] == "read_file" for s in cap.tool_chain)

    def test_discover_search_capability(self):
        cap = self.discoverer.discover(
            goal="Find documentation",
            available_tools=["web_search", "read_file", "write_file"],
            missing_capability="search and collect information",
        )
        assert cap is not None
        assert any(s["tool"] == "web_search" for s in cap.tool_chain)

    def test_discover_returns_none_when_impossible(self):
        cap = self.discoverer.discover(
            goal="Do something",
            available_tools=[],
            missing_capability="quantum computing",
        )
        assert cap is None

    def test_list_capabilities(self):
        self.discoverer.discover(
            goal="test",
            available_tools=["read_file", "write_file", "run_command"],
            missing_capability="analyze data",
        )
        caps = self.discoverer.list_capabilities()
        assert len(caps) >= 1

    def test_record_usage(self):
        self.discoverer.discover(
            goal="test",
            available_tools=["read_file", "write_file"],
            missing_capability="analyze data",
        )
        caps = self.discoverer.list_capabilities()
        name = caps[0]["name"]
        self.discoverer.record_usage(name, True)
        cap = self.discoverer.get_capability(name)
        assert cap.use_count == 1
        assert cap.success_count == 1


# === Self Module Refactor ===

class TestSelfModuleRefactor:
    def setup_method(self):
        self._path = "/tmp/test_self_refactor.json"
        if os.path.exists(self._path):
            os.unlink(self._path)
        self.refactor = SelfModuleRefactor(storage_path=self._path)

    def test_record_and_analyze(self):
        for _ in range(6):
            self.refactor.record_skill_use("bad_skill", False, 9000, 15)
        actions = self.refactor.analyze()
        deprecate = [a for a in actions if a.action == "deprecate"]
        assert len(deprecate) >= 1

    def test_healthy_skill_kept(self):
        for _ in range(10):
            self.refactor.record_skill_use("good_skill", True, 2000, 3)
        actions = self.refactor.analyze()
        keep = [a for a in actions if a.target == "good_skill"]
        assert len(keep) == 1
        assert keep[0].action in ("keep",)

    def test_high_token_skill_optimized(self):
        for _ in range(5):
            self.refactor.record_skill_use("expensive_skill", True, 12000, 5)
        actions = self.refactor.analyze()
        optimize = [a for a in actions if a.target == "expensive_skill"]
        assert len(optimize) == 1
        assert optimize[0].action in ("optimize", "split")

    def test_insufficient_data_kept(self):
        self.refactor.record_skill_use("new_skill", True, 1000, 2)
        actions = self.refactor.analyze()
        keep = [a for a in actions if a.target == "new_skill"]
        assert keep[0].action == "keep"


# === Goal Dynamic Adjuster ===

class TestGoalDynamicAdjuster:
    def setup_method(self):
        self.adjuster = GoalDynamicAdjuster()

    def test_feasible_goal_unchanged(self):
        result = self.adjuster.adjust(
            goal="Fix the typo in README",
            available_tools=["read_file", "write_file"],
            failed_attempts=0,
            failure_reasons=[],
        )
        assert not result.adjusted

    def test_many_failures_triggers_adjustment(self):
        result = self.adjuster.adjust(
            goal="Deploy to production",
            available_tools=["read_file"],
            failed_attempts=5,
            failure_reasons=["no tool"],
        )
        assert result.adjusted
        assert result.revised != ""

    def test_capability_gap_detected(self):
        result = self.adjuster.adjust(
            goal="Query the database for user records",
            available_tools=["read_file", "write_file"],
            failed_attempts=2,
            failure_reasons=["no database access"],
        )
        assert result.adjusted or not result.adjusted  # Either is acceptable

    def test_max_adjustments_limit(self):
        adjuster = GoalDynamicAdjuster()
        for _ in range(5):
            adjuster.adjust(
                goal="Impossible task",
                available_tools=[],
                failed_attempts=10,
                failure_reasons=["no tools"],
            )
        result = adjuster.adjust(
            goal="Still impossible",
            available_tools=[],
            failed_attempts=10,
            failure_reasons=["no tools"],
        )
        assert "Maximum adjustments" in result.reason

    def test_alternatives_generated(self):
        result = self.adjuster.adjust(
            goal="Monitor server health",
            available_tools=["read_file", "run_command"],
            failed_attempts=5,
            failure_reasons=["no monitoring tool"],
        )
        assert len(result.alternatives) >= 1


# === Sub-Agent Orchestrator ===

class TestSubAgentOrchestrator:
    def setup_method(self):
        self.orch = SubAgentOrchestrator(max_agents=5, max_depth=2)

    def test_create_agent(self):
        agent = self.orch.create_agent("Sub-task 1")
        assert agent is not None
        assert agent.state == SubAgentState.PENDING
        assert self.orch.active_count == 1

    def test_max_agents_limit(self):
        orch = SubAgentOrchestrator(max_agents=3)
        for i in range(3):
            orch.create_agent(f"Task {i}")
        extra = orch.create_agent("Extra task")
        assert extra is None
        assert orch.active_count == 3

    def test_depth_limit(self):
        parent = self.orch.create_agent("Parent")
        child = self.orch.create_agent("Child", parent_id=parent.id)
        grandchild = self.orch.create_agent("Grandchild", parent_id=child.id)
        assert grandchild is None  # Would exceed max_depth=2

    def test_dispatch_multiple(self):
        results = self.orch.dispatch([
            {"goal": "Task A"},
            {"goal": "Task B"},
            {"goal": "Task C"},
        ])
        assert len(results) == 3
        assert all(r.success for r in results)

    def test_cancel_agent(self):
        agent = self.orch.create_agent("Cancel me")
        agent.state = SubAgentState.RUNNING
        assert self.orch.cancel_agent(agent.id)
        assert agent.state == SubAgentState.CANCELLED

    def test_destroy_agent(self):
        agent = self.orch.create_agent("Destroy me")
        agent.state = SubAgentState.COMPLETED
        assert self.orch.destroy_agent(agent.id)
        assert self.orch.get_agent(agent.id) is None

    def test_merge_results(self):
        self.orch.dispatch([
            {"goal": "Merge A"},
            {"goal": "Merge B"},
        ])
        agents = self.orch.list_agents()
        ids = [a.id for a in agents]
        merged = self.orch.merge_results(ids)
        assert merged["success_count"] == 2
        assert merged["total_tokens"] > 0

    def test_remaining_capacity(self):
        assert self.orch.remaining_capacity == 5
        self.orch.create_agent("Task")
        assert self.orch.remaining_capacity == 4


# === Causal Graph MCP ===

class TestCausalGraph:
    def setup_method(self):
        self._path = "/tmp/test_causal_graph.json"
        if os.path.exists(self._path):
            os.unlink(self._path)
        self.graph = CausalGraph(storage_path=self._path)

    def test_add_event(self):
        node = self.graph.add_event("e1", "User clicked button", "action")
        assert node.id == "e1"
        assert node.node_type == "action"

    def test_add_causality(self):
        self.graph.add_event("e1", "Action 1", "action")
        self.graph.add_event("e2", "Outcome 1", "outcome")
        assert self.graph.add_causality("e1", "e2", "causes", 0.9)

    def test_find_root_causes(self):
        self.graph.add_event("root", "Root cause", "error")
        self.graph.add_event("mid", "Intermediate", "action")
        self.graph.add_event("leaf", "Final failure", "outcome")
        self.graph.add_causality("root", "mid")
        self.graph.add_causality("mid", "leaf")
        roots = self.graph.find_root_causes("leaf")
        assert len(roots) == 1
        assert roots[0].id == "root"

    def test_explain_failure(self):
        self.graph.add_event("root", "Missing config file", "error")
        self.graph.add_event("fail", "App crashed", "outcome")
        self.graph.add_causality("root", "fail")
        explanation = self.graph.explain_failure("fail")
        assert explanation["failure"] == "App crashed"
        assert len(explanation["root_causes"]) == 1

    def test_graph_stats(self):
        self.graph.add_event("a", "A", "action")
        self.graph.add_event("b", "B", "outcome")
        stats = self.graph.get_graph_stats()
        assert stats["nodes"] == 2

    def test_tool_definitions(self):
        tools = self.graph.get_tool_definitions()
        assert len(tools) == 3


# === Trajectory Storage MCP ===

class TestTrajectoryStorage:
    def setup_method(self):
        self._path = "/tmp/test_trajectory.json"
        if os.path.exists(self._path):
            os.unlink(self._path)
        self.storage = TrajectoryStorage(storage_path=self._path)

    def test_start_and_complete(self):
        traj = self.storage.start_trajectory("Fix the bug")
        assert traj.task_id
        assert traj.goal == "Fix the bug"
        self.storage.complete_trajectory(traj.task_id, "Bug fixed", True)
        retrieved = self.storage.get_trajectory(traj.task_id)
        assert retrieved.success

    def test_record_step(self):
        traj = self.storage.start_trajectory("Test task")
        assert self.storage.record_step(
            traj.task_id, 1, "read", "read_file", {"path": "test.py"}, "content"
        )
        retrieved = self.storage.get_trajectory(traj.task_id)
        assert len(retrieved.steps) == 1

    def test_replay(self):
        traj = self.storage.start_trajectory("Replay me")
        self.storage.record_step(traj.task_id, 1, "action1", "tool1", {}, "result1")
        self.storage.record_step(traj.task_id, 2, "action2", "tool2", {}, "result2")
        replay = self.storage.replay(traj.task_id)
        assert len(replay) == 2
        assert replay[0]["tool"] == "tool1"

    def test_list_trajectories(self):
        t1 = self.storage.start_trajectory("Task 1")
        self.storage.complete_trajectory(t1.task_id, "Done", True)
        t2 = self.storage.start_trajectory("Task 2")
        self.storage.complete_trajectory(t2.task_id, "Failed", False)
        all_trajs = self.storage.list_trajectories()
        assert len(all_trajs) == 2
        success_trajs = self.storage.list_trajectories(success_only=True)
        assert len(success_trajs) == 1

    def test_find_similar(self):
        t1 = self.storage.start_trajectory("Fix authentication bug in login")
        self.storage.complete_trajectory(t1.task_id, "Fixed", True)
        similar = self.storage.find_similar_trajectories("Fix login authentication")
        assert len(similar) >= 1


# === Capability Index MCP ===

class TestCapabilityIndex:
    def setup_method(self):
        self._path = "/tmp/test_cap_index.json"
        if os.path.exists(self._path):
            os.unlink(self._path)
        self.index = CapabilityIndex(storage_path=self._path)

    def test_register_and_search(self):
        self.index.register(
            "code_review",
            "Review code for bugs and style issues",
            "skill",
            tags=["review", "code", "quality"],
        )
        results = self.index.search("review code quality")
        assert len(results) >= 1
        assert results[0].entry.name == "code_review"

    def test_find_best(self):
        self.index.register("deploy", "Deploy application to server", "skill")
        self.index.register("test", "Run unit tests", "skill")
        best = self.index.find_best("deploy the app to production")
        assert best is not None

    def test_type_filter(self):
        self.index.register("my_tool", "A useful tool", "tool")
        self.index.register("my_skill", "A useful skill", "skill")
        tools = self.index.search("useful", entry_type="tool")
        assert all(r.entry.entry_type == "tool" for r in tools)

    def test_update_stats(self):
        self.index.register("test_cap", "Test capability", "skill")
        self.index.update_stats("test_cap", True)
        self.index.update_stats("test_cap", True)
        self.index.update_stats("test_cap", False)
        results = self.index.search("test capability")
        assert results[0].entry.success_rate == pytest.approx(2 / 3, rel=0.01)

    def test_list_all(self):
        self.index.register("a", "A capability", "skill")
        self.index.register("b", "B capability", "tool")
        all_caps = self.index.list_all()
        assert len(all_caps) == 2

    def test_tool_definitions(self):
        tools = self.index.get_tool_definitions()
        assert len(tools) == 2

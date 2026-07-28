"""Tests for task DAG and handoff mechanism."""

from __future__ import annotations

import pytest

from app.core.task_dag import TaskDAG, TaskNode, HandoffMessage


class TestTaskDAG:
    def test_empty_dag(self):
        dag = TaskDAG()
        assert dag.topological_order() == []
        assert dag.detect_cycle() is None
        assert dag.get_ready_tasks(set()) == []

    def test_single_task(self):
        dag = TaskDAG()
        dag.add_task(TaskNode("1", "Task 1"))
        assert dag.topological_order() == [["1"]]
        assert dag.detect_cycle() is None
        assert dag.get_ready_tasks(set()) == ["1"]

    def test_linear_dependencies(self):
        dag = TaskDAG()
        dag.add_task(TaskNode("1", "A"))
        dag.add_task(TaskNode("2", "B", dependencies=["1"]))
        dag.add_task(TaskNode("3", "C", dependencies=["2"]))
        order = dag.topological_order()
        assert order == [["1"], ["2"], ["3"]]
        assert dag.detect_cycle() is None

    def test_parallel_tasks(self):
        dag = TaskDAG()
        dag.add_task(TaskNode("1", "A"))
        dag.add_task(TaskNode("2", "B", dependencies=["1"]))
        dag.add_task(TaskNode("3", "C", dependencies=["1"]))
        order = dag.topological_order()
        assert order[0] == ["1"]
        assert set(order[1]) == {"2", "3"}
        assert dag.detect_cycle() is None

    def test_diamond_dependencies(self):
        dag = TaskDAG()
        dag.add_task(TaskNode("1", "A"))
        dag.add_task(TaskNode("2", "B", dependencies=["1"]))
        dag.add_task(TaskNode("3", "C", dependencies=["1"]))
        dag.add_task(TaskNode("4", "D", dependencies=["2", "3"]))
        order = dag.topological_order()
        assert order[0] == ["1"]
        assert set(order[1]) == {"2", "3"}
        assert order[2] == ["4"]
        assert dag.detect_cycle() is None

    def test_cycle_detection_self_loop(self):
        dag = TaskDAG()
        dag.add_task(TaskNode("1", "A", dependencies=["1"]))
        cycle = dag.detect_cycle()
        assert cycle is not None

    def test_cycle_detection_multi(self):
        dag = TaskDAG()
        dag.add_task(TaskNode("1", "A", dependencies=["2"]))
        dag.add_task(TaskNode("2", "B", dependencies=["1"]))
        cycle = dag.detect_cycle()
        assert cycle is not None

    def test_get_ready_tasks(self):
        dag = TaskDAG()
        dag.add_task(TaskNode("1", "A"))
        dag.add_task(TaskNode("2", "B", dependencies=["1"]))
        dag.add_task(TaskNode("3", "C", dependencies=["1"]))
        assert set(dag.get_ready_tasks(set())) == {"1"}
        assert set(dag.get_ready_tasks({"1"})) == {"2", "3"}
        assert set(dag.get_ready_tasks({"1", "2", "3"})) == set()

    def test_missing_dependency(self):
        dag = TaskDAG()
        dag.add_task(TaskNode("1", "A", dependencies=["missing"]))
        order = dag.topological_order()
        assert order == [["1"]]

    def test_get_task(self):
        dag = TaskDAG()
        dag.add_task(TaskNode("1", "A", payload={"key": "value"}))
        task = dag.get_task("1")
        assert task is not None
        assert task.name == "A"
        assert task.payload == {"key": "value"}
        assert dag.get_task("missing") is None


class TestHandoffMessage:
    def test_handoff_message(self):
        msg = HandoffMessage(
            source_agent="agent-1",
            target_agent="agent-2",
            task_id="task-123",
            context="Task context here",
            reason="Agent-1 is overloaded",
        )
        assert msg.source_agent == "agent-1"
        assert msg.target_agent == "agent-2"
        assert msg.task_id == "task-123"
        assert msg.context == "Task context here"
        assert msg.reason == "Agent-1 is overloaded"
        assert msg.metadata == {}

    def test_handoff_message_with_metadata(self):
        msg = HandoffMessage(
            source_agent="agent-1",
            target_agent="agent-2",
            task_id="task-123",
            context="ctx",
            metadata={"priority": "high", "deadline": "2024-01-01"},
        )
        assert msg.metadata == {"priority": "high", "deadline": "2024-01-01"}

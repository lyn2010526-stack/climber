"""Tests for multi-agent shared state persistence and dynamic DAG updates."""

from __future__ import annotations

import pytest

from app.core.task_dag import TaskDAG, TaskNode


class TestDynamicDAGUpdates:
    def test_update_task_dependencies_no_cycle(self):
        dag = TaskDAG()
        dag.add_task(TaskNode("1", "A"))
        dag.add_task(TaskNode("2", "B", dependencies=["1"]))
        dag.add_task(TaskNode("3", "C"))

        result = dag.update_task_dependencies("3", ["1"])
        assert result is True
        assert dag.get_task("3").dependencies == ["1"]

    def test_update_task_dependencies_creates_cycle(self):
        dag = TaskDAG()
        dag.add_task(TaskNode("1", "A", dependencies=["2"]))
        dag.add_task(TaskNode("2", "B", dependencies=["1"]))

        result = dag.update_task_dependencies("1", ["2", "3"])
        assert result is False

    def test_update_task_dependencies_missing_task(self):
        dag = TaskDAG()
        dag.add_task(TaskNode("1", "A"))

        result = dag.update_task_dependencies("missing", ["1"])
        assert result is False

    def test_update_task_dependencies_clears_deps(self):
        dag = TaskDAG()
        dag.add_task(TaskNode("1", "A", dependencies=["2"]))
        dag.add_task(TaskNode("2", "B"))

        result = dag.update_task_dependencies("1", [])
        assert result is True
        assert dag.get_task("1").dependencies == []

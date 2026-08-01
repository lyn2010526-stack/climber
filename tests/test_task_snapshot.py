"""Tests for the standardized task snapshot structure."""

from __future__ import annotations

import pytest

from app.core.task_snapshot import (
    ContextSummary,
    PlanStep,
    StepStatus,
    ToolCallStatus,
    TaskConstraints,
    TaskSnapshot,
    ToolCallRecord,
)


class TestPlanStep:
    def test_create_step(self) -> None:
        step = PlanStep(id="step-1", description="Do something")
        assert step.status == StepStatus.PENDING
        assert step.result is None

    def test_step_to_dict(self) -> None:
        step = PlanStep(
            id="step-1",
            description="Do something",
            status=StepStatus.COMPLETED,
            result="Done",
        )
        data = step.to_dict()
        assert data["id"] == "step-1"
        assert data["status"] == "completed"


class TestToolCallRecord:
    def test_create_record(self) -> None:
        record = ToolCallRecord(
            tool_name="read_file",
            arguments={"path": "/test.txt"},
            status=ToolCallStatus.SUCCESS,
            result="file content",
        )
        assert record.tool_name == "read_file"
        assert record.attempt == 1

    def test_record_to_dict(self) -> None:
        record = ToolCallRecord(
            tool_name="test",
            arguments={},
            status=ToolCallStatus.FAILED,
            error="Not found",
        )
        data = record.to_dict()
        assert data["status"] == "failed"
        assert data["error"] == "Not found"


class TestContextSummary:
    def test_empty_summary(self) -> None:
        summary = ContextSummary()
        assert summary.format_for_prompt() == ""

    def test_with_key_facts(self) -> None:
        summary = ContextSummary(key_facts=["Fact 1", "Fact 2"])
        formatted = summary.format_for_prompt()
        assert "KEY FACTS" in formatted
        assert "Fact 1" in formatted

    def test_with_files_modified(self) -> None:
        summary = ContextSummary(files_modified=["file1.py", "file2.py"])
        formatted = summary.format_for_prompt()
        assert "FILES MODIFIED" in formatted
        assert "file1.py" in formatted

    def test_to_dict(self) -> None:
        summary = ContextSummary(key_facts=["fact"], decisions_made=["decision"])
        data = summary.to_dict()
        assert data["key_facts"] == ["fact"]
        assert data["decisions_made"] == ["decision"]


class TestTaskConstraints:
    def test_default_constraints(self) -> None:
        constraints = TaskConstraints()
        assert constraints.max_iterations == 50
        assert constraints.permission_level == "standard"

    def test_to_dict(self) -> None:
        constraints = TaskConstraints(max_iterations=100, permission_level="high_risk")
        data = constraints.to_dict()
        assert data["max_iterations"] == 100
        assert data["permission_level"] == "high_risk"


class TestTaskSnapshot:
    def test_create_snapshot(self) -> None:
        snapshot = TaskSnapshot(task_id="task-1", objective="Build API")
        assert snapshot.task_id == "task-1"
        assert snapshot.objective == "Build API"
        assert snapshot.status == "pending"

    def test_add_step(self) -> None:
        snapshot = TaskSnapshot(task_id="task-1")
        step = snapshot.add_step("Step 1: Research")
        assert step.id == "step-1"
        assert step.status == StepStatus.PENDING
        assert len(snapshot.plan) == 1
        assert "step-1" in snapshot.execution_queue

    def test_start_step(self) -> None:
        snapshot = TaskSnapshot(task_id="task-1")
        snapshot.add_step("Step 1")
        snapshot.start_step("step-1")
        assert snapshot.plan[0].status == StepStatus.RUNNING
        assert snapshot.current_step_id == "step-1"
        assert "step-1" not in snapshot.execution_queue

    def test_complete_step(self) -> None:
        snapshot = TaskSnapshot(task_id="task-1")
        snapshot.add_step("Step 1")
        snapshot.start_step("step-1")
        snapshot.complete_step("step-1", result="Done")
        assert snapshot.plan[0].status == StepStatus.COMPLETED
        assert snapshot.plan[0].result == "Done"

    def test_fail_step(self) -> None:
        snapshot = TaskSnapshot(task_id="task-1")
        snapshot.add_step("Step 1")
        snapshot.start_step("step-1")
        snapshot.fail_step("step-1", error="File not found")
        assert snapshot.plan[0].status == StepStatus.FAILED
        assert "File not found" in snapshot.context_summary.errors_encountered[0]

    def test_record_tool_call(self) -> None:
        snapshot = TaskSnapshot(task_id="task-1")
        record = snapshot.record_tool_call(
            "read_file",
            {"path": "/test.txt"},
            ToolCallStatus.SUCCESS,
            result="content",
        )
        assert record.tool_name == "read_file"
        assert snapshot.total_tool_calls == 1
        assert snapshot.last_tool_call is record

    def test_record_multiple_tool_calls(self) -> None:
        snapshot = TaskSnapshot(task_id="task-1")
        snapshot.record_tool_call("tool_a", {}, ToolCallStatus.SUCCESS)
        snapshot.record_tool_call("tool_a", {}, ToolCallStatus.SUCCESS)
        snapshot.record_tool_call("tool_b", {}, ToolCallStatus.FAILED, error="err")
        assert snapshot.total_tool_calls == 3

    def test_get_pending_steps(self) -> None:
        snapshot = TaskSnapshot(task_id="task-1")
        snapshot.add_step("Step 1")
        snapshot.add_step("Step 2")
        snapshot.complete_step("step-1")
        pending = snapshot.get_pending_steps()
        assert len(pending) == 1
        assert pending[0].id == "step-2"

    def test_get_failed_steps(self) -> None:
        snapshot = TaskSnapshot(task_id="task-1")
        snapshot.add_step("Step 1")
        snapshot.add_step("Step 2")
        snapshot.fail_step("step-1", error="error")
        failed = snapshot.get_failed_steps()
        assert len(failed) == 1

    def test_get_progress(self) -> None:
        snapshot = TaskSnapshot(task_id="task-1")
        snapshot.add_step("Step 1")
        snapshot.add_step("Step 2")
        snapshot.add_step("Step 3")
        snapshot.complete_step("step-1")
        snapshot.fail_step("step-2", error="err")
        progress = snapshot.get_progress()
        assert progress["completed"] == 1
        assert progress["failed"] == 1
        assert progress["pending"] == 1

    def test_is_complete(self) -> None:
        snapshot = TaskSnapshot(task_id="task-1")
        assert not snapshot.is_complete()

        snapshot.add_step("Step 1")
        snapshot.complete_step("step-1")
        assert snapshot.is_complete()

    def test_has_failures(self) -> None:
        snapshot = TaskSnapshot(task_id="task-1")
        snapshot.add_step("Step 1")
        assert not snapshot.has_failures()

        snapshot.fail_step("step-1", error="err")
        assert snapshot.has_failures()

    def test_should_continue(self) -> None:
        snapshot = TaskSnapshot(task_id="task-1")
        snapshot.add_step("Step 1")
        assert snapshot.should_continue()

        snapshot.complete_step("step-1")
        assert not snapshot.should_continue()

    def test_should_continue_with_max_iterations(self) -> None:
        snapshot = TaskSnapshot(task_id="task-1")
        snapshot.constraints.max_iterations = 5
        snapshot.add_step("Step 1")
        snapshot.iteration = 5
        assert not snapshot.should_continue()

    def test_format_context_for_prompt(self) -> None:
        snapshot = TaskSnapshot(task_id="task-1", objective="Test objective")
        snapshot.add_step("Step 1")
        formatted = snapshot.format_context_for_prompt()
        assert "Test objective" in formatted
        assert "0/1 steps complete" in formatted

    def test_to_dict(self) -> None:
        snapshot = TaskSnapshot(task_id="task-1", objective="Test")
        snapshot.add_step("Step 1")
        data = snapshot.to_dict()
        assert data["task_id"] == "task-1"
        assert data["objective"] == "Test"
        assert len(data["plan"]) == 1

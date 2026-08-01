"""Tests for Phase 3 modules."""

import os
import pytest
from app.core.metacognition.memory_pruner import LongTermMemoryPruner
from app.tools.mcp_plugins.inter_agent_comm import (
    InterAgentCommunication, MessageType, MessagePriority,
)
from app.tools.mcp_plugins.time_scheduler import (
    TimeEventScheduler, TaskStatus, TaskFrequency,
)


# === Memory Pruner ===

class TestMemoryPruner:
    def setup_method(self):
        self._path = "/tmp/test_memory_pruner.json"
        if os.path.exists(self._path):
            os.unlink(self._path)
        self.pruner = LongTermMemoryPruner(storage_path=self._path, max_entries=100)

    def test_add_and_access(self):
        self.pruner.add_memory("m1", "Important fact about auth", 0.8)
        entry = self.pruner.access_memory("m1")
        assert entry is not None
        assert entry.access_count == 1

    def test_prune_removes_low_value(self):
        for i in range(120):
            self.pruner.add_memory(f"m{i}", f"Memory content {i}", 0.1)
        result = self.pruner.prune(force=True)
        assert result.pruned_count < 120

    def test_merge_similar(self):
        self.pruner.add_memory("m1", "Fix auth bug in login module", 0.7)
        self.pruner.add_memory("m2", "Fix auth bug in login module", 0.7)
        self.pruner.add_memory("m3", "Unrelated memory about databases", 0.5)
        result = self.pruner.prune()
        assert result.merged_count >= 1

    def test_search(self):
        self.pruner.add_memory("m1", "Authentication system uses JWT tokens", 0.8)
        self.pruner.add_memory("m2", "Database uses PostgreSQL", 0.6)
        results = self.pruner.search("authentication JWT")
        assert len(results) >= 1
        assert "auth" in results[0].content.lower()

    def test_stats(self):
        self.pruner.add_memory("m1", "Test memory", 0.5)
        stats = self.pruner.get_stats()
        assert stats["count"] == 1


# === Inter-Agent Communication ===

class TestInterAgentCommunication:
    def setup_method(self):
        self._path = "/tmp/test_agent_comm.json"
        if os.path.exists(self._path):
            os.unlink(self._path)
        self.comm = InterAgentCommunication(storage_path=self._path)

    def test_send_and_receive(self):
        self.comm.send("agent_a", "agent_b", MessageType.TASK_ASSIGN, {"goal": "fix bug"})
        msgs = self.comm.receive("agent_b")
        assert len(msgs) == 1
        assert msgs[0].sender == "agent_a"

    def test_broadcast(self):
        msgs = self.comm.broadcast(
            "orchestrator", ["a1", "a2", "a3"],
            MessageType.TASK_ASSIGN, {"goal": "sub-task"},
        )
        assert len(msgs) == 3

    def test_conflict_resolution(self):
        conflict = self.comm.report_conflict(
            "agent_a", ["agent_a", "agent_b"],
            "Resource conflict: both agents trying to write same file",
        )
        assert len(conflict.proposed_resolution) > 0

    def test_merge_results(self):
        self.comm.send("a1", "orchestrator", MessageType.RESULT_REPORT, {"result": "partial A"})
        self.comm.send("a2", "orchestrator", MessageType.RESULT_REPORT, {"result": "partial B"})
        merged = self.comm.merge_results(["orchestrator"])
        assert merged["merged"]

    def test_unread_count(self):
        self.comm.send("sender", "recipient", MessageType.STATUS_UPDATE, {})
        assert self.comm.get_unread_count("recipient") == 1


# === Time Event Scheduler ===

class TestTimeEventScheduler:
    def setup_method(self):
        self._path = "/tmp/test_scheduler.json"
        if os.path.exists(self._path):
            os.unlink(self._path)
        self.scheduler = TimeEventScheduler(storage_path=self._path)

    def test_schedule_task(self):
        task = self.scheduler.schedule(
            "cleanup", "Clean temp files", 0, TaskFrequency.ONCE,
        )
        assert task.status == TaskStatus.PENDING

    def test_get_due_tasks(self):
        self.scheduler.task1 = self.scheduler.schedule("t1", "Due now", 0)
        self.scheduler.schedule("t2", "Future", 99999)
        due = self.scheduler.get_due_tasks()
        assert len(due) >= 1

    def test_execute_task(self):
        task = self.scheduler.schedule("exec_me", "Task to execute", 0)
        result = self.scheduler.execute_task(task.id)
        assert result["status"] == TaskStatus.COMPLETED.value

    def test_recurring_task(self):
        task = self.scheduler.schedule(
            "recurring", "Daily check", 0,
            TaskFrequency.DAILY, max_runs=3,
        )
        self.scheduler.execute_task(task.id)
        updated = self.scheduler.get_task(task.id)
        assert updated.run_count == 1
        assert updated.status == TaskStatus.PENDING  # Still pending for next run

    def test_cancel_task(self):
        task = self.scheduler.schedule("cancel_me", "Cancel this", 100)
        assert self.scheduler.cancel_task(task.id)
        assert self.scheduler.get_task(task.id).status == TaskStatus.CANCELLED

    def test_list_tasks(self):
        self.scheduler.schedule("t1", "Task 1", 0)
        self.scheduler.schedule("t2", "Task 2", 999)
        tasks = self.scheduler.list_tasks()
        assert len(tasks) == 2

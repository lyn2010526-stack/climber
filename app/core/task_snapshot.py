"""Standardized task snapshot structure.

Provides a unified representation of task state including:
- Goal and plan (what to achieve and how)
- Execution queue (pending steps to execute)
- Tool call state (last tool invocation and status)
- Context summary (condensed conversation context)
- Constraints (permissions, limits, safety rules)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class ToolCallStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    DENIED = "denied"
    INVALID_INPUT = "invalid_input"


@dataclass
class PlanStep:
    """A single step in the task plan."""

    id: str
    description: str
    status: StepStatus = StepStatus.PENDING
    tool_name: str | None = None
    tool_arguments: dict[str, Any] = field(default_factory=dict)
    result: str | None = None
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "tool_name": self.tool_name,
            "tool_arguments": self.tool_arguments,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "dependencies": self.dependencies,
        }


@dataclass
class ToolCallRecord:
    """Record of a tool invocation."""

    tool_name: str
    arguments: dict[str, Any]
    status: ToolCallStatus = ToolCallStatus.SUCCESS
    result: str | None = None
    error: str | None = None
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    attempt: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
            "attempt": self.attempt,
        }


@dataclass
class ContextSummary:
    """Condensed conversation context for prompt injection."""

    key_facts: list[str] = field(default_factory=list)
    decisions_made: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    errors_encountered: list[str] = field(default_factory=list)
    user_preferences: dict[str, str] = field(default_factory=dict)

    def format_for_prompt(self) -> str:
        """Format as a compact prompt snippet."""
        parts: list[str] = []

        if self.key_facts:
            parts.append("[KEY FACTS]")
            parts.extend(f"- {f}" for f in self.key_facts)

        if self.decisions_made:
            parts.append("[DECISIONS MADE]")
            parts.extend(f"- {d}" for d in self.decisions_made)

        if self.files_modified:
            parts.append("[FILES MODIFIED]")
            parts.extend(f"- {f}" for f in self.files_modified[-10:])

        if self.errors_encountered:
            parts.append("[RECENT ERRORS]")
            parts.extend(f"- {e}" for e in self.errors_encountered[-5:])

        if self.user_preferences:
            parts.append("[USER PREFERENCES]")
            for k, v in self.user_preferences.items():
                parts.append(f"- {k}: {v}")

        return "\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key_facts": self.key_facts,
            "decisions_made": self.decisions_made,
            "files_modified": self.files_modified,
            "errors_encountered": self.errors_encountered,
            "user_preferences": self.user_preferences,
        }


@dataclass
class TaskConstraints:
    """Runtime constraints for the task."""

    max_iterations: int = 50
    max_tool_calls: int = 100
    max_duration_seconds: int = 600
    permission_level: str = "standard"
    allowed_tools: list[str] = field(default_factory=list)
    denied_tools: list[str] = field(default_factory=list)
    sandbox_enabled: bool = False
    allow_network: bool = True
    allow_file_write: bool = True
    custom_rules: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_iterations": self.max_iterations,
            "max_tool_calls": self.max_tool_calls,
            "max_duration_seconds": self.max_duration_seconds,
            "permission_level": self.permission_level,
            "allowed_tools": self.allowed_tools,
            "denied_tools": self.denied_tools,
            "sandbox_enabled": self.sandbox_enabled,
            "allow_network": self.allow_network,
            "allow_file_write": self.allow_file_write,
            "custom_rules": self.custom_rules,
        }


@dataclass
class TaskSnapshot:
    """Complete task snapshot — the single source of truth for task state."""

    task_id: str
    objective: str = ""
    plan: list[PlanStep] = field(default_factory=list)
    execution_queue: list[str] = field(default_factory=list)
    current_step_id: str | None = None
    tool_call_history: list[ToolCallRecord] = field(default_factory=list)
    last_tool_call: ToolCallRecord | None = None
    context_summary: ContextSummary = field(default_factory=ContextSummary)
    constraints: TaskConstraints = field(default_factory=TaskConstraints)
    status: str = "pending"
    iteration: int = 0
    total_tool_calls: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_step(self, description: str, step_id: str | None = None, **kwargs: Any) -> PlanStep:
        """Add a step to the plan."""
        step = PlanStep(
            id=step_id or f"step-{len(self.plan) + 1}",
            description=description,
            **kwargs,
        )
        self.plan.append(step)
        self.execution_queue.append(step.id)
        self._touch()
        return step

    def start_step(self, step_id: str) -> None:
        """Mark a step as running."""
        for step in self.plan:
            if step.id == step_id:
                step.status = StepStatus.RUNNING
                step.started_at = datetime.now(timezone.utc).isoformat()
                self.current_step_id = step_id
                if step_id in self.execution_queue:
                    self.execution_queue.remove(step_id)
                self._touch()
                return

    def complete_step(self, step_id: str, result: str | None = None) -> None:
        """Mark a step as completed."""
        for step in self.plan:
            if step.id == step_id:
                step.status = StepStatus.COMPLETED
                step.completed_at = datetime.now(timezone.utc).isoformat()
                step.result = result
                self._touch()
                return

    def fail_step(self, step_id: str, error: str) -> None:
        """Mark a step as failed."""
        for step in self.plan:
            if step.id == step_id:
                step.status = StepStatus.FAILED
                step.error = error
                step.completed_at = datetime.now(timezone.utc).isoformat()
                self.context_summary.errors_encountered.append(
                    f"Step '{step.description}': {error}"
                )
                self._touch()
                return

    def record_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        status: ToolCallStatus,
        result: str | None = None,
        error: str | None = None,
        duration_ms: float = 0.0,
    ) -> ToolCallRecord:
        """Record a tool call in the history."""
        record = ToolCallRecord(
            tool_name=tool_name,
            arguments=arguments,
            status=status,
            result=result,
            error=error,
            duration_ms=duration_ms,
            attempt=self._count_tool_attempts(tool_name) + 1,
        )
        self.tool_call_history.append(record)
        self.last_tool_call = record
        self.total_tool_calls += 1
        self._touch()
        return record

    def _count_tool_attempts(self, tool_name: str) -> int:
        """Count how many times a tool has been called."""
        return sum(1 for r in self.tool_call_history if r.tool_name == tool_name)

    def get_pending_steps(self) -> list[PlanStep]:
        """Get all pending steps."""
        return [s for s in self.plan if s.status == StepStatus.PENDING]

    def get_failed_steps(self) -> list[PlanStep]:
        """Get all failed steps."""
        return [s for s in self.plan if s.status == StepStatus.FAILED]

    def get_progress(self) -> dict[str, int]:
        """Get task progress counts."""
        counts: dict[str, int] = {s.value: 0 for s in StepStatus}
        for step in self.plan:
            counts[step.status.value] += 1
        return counts

    def is_complete(self) -> bool:
        """Check if all steps are completed."""
        return bool(self.plan) and all(s.status == StepStatus.COMPLETED for s in self.plan)

    def has_failures(self) -> bool:
        """Check if any steps have failed."""
        return any(s.status == StepStatus.FAILED for s in self.plan)

    def should_continue(self) -> bool:
        """Check if the task should continue executing."""
        if self.is_complete():
            return False
        if self.iteration >= self.constraints.max_iterations:
            return False
        if self.total_tool_calls >= self.constraints.max_tool_calls:
            return False
        return bool(self.get_pending_steps()) or bool(self.get_failed_steps())

    def format_context_for_prompt(self) -> str:
        """Format the full context summary for prompt injection."""
        parts: list[str] = []

        if self.objective:
            parts.append(f"[TASK OBJECTIVE]\n{self.objective}")

        progress = self.get_progress()
        parts.append(
            f"[PROGRESS] {progress.get('completed', 0)}/{len(self.plan)} steps complete, "
            f"{progress.get('failed', 0)} failed, {progress.get('pending', 0)} pending"
        )

        if self.current_step_id:
            for step in self.plan:
                if step.id == self.current_step_id:
                    parts.append(f"[CURRENT STEP] {step.description}")
                    break

        context = self.context_summary.format_for_prompt()
        if context:
            parts.append(context)

        if self.constraints.custom_rules:
            parts.append("[ACTIVE CONSTRAINTS]")
            parts.extend(f"- {r}" for r in self.constraints.custom_rules)

        return "\n\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "task_id": self.task_id,
            "objective": self.objective,
            "plan": [s.to_dict() for s in self.plan],
            "execution_queue": self.execution_queue,
            "current_step_id": self.current_step_id,
            "tool_call_history": [r.to_dict() for r in self.tool_call_history[-50:]],
            "last_tool_call": self.last_tool_call.to_dict() if self.last_tool_call else None,
            "context_summary": self.context_summary.to_dict(),
            "constraints": self.constraints.to_dict(),
            "status": self.status,
            "iteration": self.iteration,
            "total_tool_calls": self.total_tool_calls,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    def _touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(timezone.utc).isoformat()

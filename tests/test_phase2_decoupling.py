"""Tests for Phase 2 architecture decoupling.

Covers: exception hierarchy, state machine unification,
session status mapping, and protocol classes.
"""

from __future__ import annotations

import pytest

from app.core import SessionStatus
from app.core.exceptions import (
    AgentEngineError,
    EnsembleError,
    InvalidStateTransitionError,
    MemoryRetrievalError,
    PipelineError,
    SecurityViolationError,
    SessionNotFoundError,
    SubagentError,
    ToolExecutionError,
)
from app.core.task_state_machine import (
    StateTransitionError,
    TaskState,
    TaskStateMachine,
    to_session_status,
)
from app.core.scheduler_abstraction import TaskState as SchedulerTaskState


class TestExceptionHierarchy:
    """Each exception type can be raised and caught."""

    def test_agent_engine_error_is_base(self):
        with pytest.raises(AgentEngineError):
            raise AgentEngineError("base error")

    def test_session_not_found_error(self):
        with pytest.raises(SessionNotFoundError):
            raise SessionNotFoundError("session-123")

    def test_session_not_found_is_agent_engine_error(self):
        with pytest.raises(AgentEngineError):
            raise SessionNotFoundError("session-123")

    def test_invalid_state_transition_error(self):
        with pytest.raises(InvalidStateTransitionError):
            raise InvalidStateTransitionError("bad transition")

    def test_invalid_state_transition_is_agent_engine_error(self):
        with pytest.raises(AgentEngineError):
            raise InvalidStateTransitionError("bad transition")

    def test_tool_execution_error_fields(self):
        err = ToolExecutionError("search", details="timeout")
        assert err.tool_name == "search"
        assert err.details == "timeout"
        assert "search" in str(err)

    def test_tool_execution_error_is_agent_engine_error(self):
        with pytest.raises(AgentEngineError):
            raise ToolExecutionError("search", details="timeout")

    def test_memory_retrieval_error(self):
        with pytest.raises(MemoryRetrievalError):
            raise MemoryRetrievalError("vector db down")

    def test_memory_retrieval_is_agent_engine_error(self):
        with pytest.raises(AgentEngineError):
            raise MemoryRetrievalError("vector db down")

    def test_security_violation_error_field(self):
        err = SecurityViolationError("command_injection", detail="rm -rf /")
        assert err.violation_type == "command_injection"
        assert "command_injection" in str(err)

    def test_security_violation_is_agent_engine_error(self):
        with pytest.raises(AgentEngineError):
            raise SecurityViolationError("command_injection")

    def test_subagent_error_fields(self):
        err = SubagentError("sub-1", depth=2, detail="timeout")
        assert err.subagent_id == "sub-1"
        assert err.depth == 2
        assert "sub-1" in str(err)

    def test_subagent_error_is_agent_engine_error(self):
        with pytest.raises(AgentEngineError):
            raise SubagentError("sub-1", depth=2)

    def test_pipeline_error_field(self):
        err = PipelineError("router", detail="no route found")
        assert err.step_name == "router"
        assert "router" in str(err)

    def test_pipeline_error_is_agent_engine_error(self):
        with pytest.raises(AgentEngineError):
            raise PipelineError("router")

    def test_ensemble_error_field(self):
        err = EnsembleError(["gpt-4", "claude-3"], detail="consensus failed")
        assert err.model_ids == ["gpt-4", "claude-3"]
        assert "gpt-4" in str(err)

    def test_ensemble_error_is_agent_engine_error(self):
        with pytest.raises(AgentEngineError):
            raise EnsembleError(["gpt-4"])

    def test_catch_all_agent_engine_error(self):
        """All specific exceptions are catchable as AgentEngineError."""
        exceptions = [
            SessionNotFoundError("s"),
            InvalidStateTransitionError("t"),
            ToolExecutionError("tool"),
            MemoryRetrievalError("m"),
            SecurityViolationError("v"),
            SubagentError("sub", depth=1),
            PipelineError("step"),
            EnsembleError(["m"]),
        ]
        for exc in exceptions:
            with pytest.raises(AgentEngineError):
                raise exc


class TestStateMachineUnification:
    """TaskState imported from scheduler_abstraction is same as from task_state_machine."""

    def test_same_enum_identity(self):
        assert SchedulerTaskState is TaskState

    def test_scheduler_task_state_has_all_values(self):
        values = {s.value for s in SchedulerTaskState}
        assert "pending" in values
        assert "assigned" in values
        assert "running" in values
        assert "waiting" in values
        assert "completed" in values
        assert "failed" in values
        assert "cancelled" in values

    def test_task_state_has_processing_paused_retrying(self):
        values = {s.value for s in TaskState}
        assert "processing" in values
        assert "paused" in values
        assert "retrying" in values

    def test_state_transition_error_alias(self):
        assert StateTransitionError is InvalidStateTransitionError

    def test_invalid_transition_raises_new_error(self):
        sm = TaskStateMachine("t1")
        with pytest.raises(InvalidStateTransitionError):
            import asyncio
            asyncio.run(sm.transition(TaskState.COMPLETED, trigger="bad"))

    def test_invalid_transition_also_raises_alias(self):
        sm = TaskStateMachine("t1")
        with pytest.raises(StateTransitionError):
            import asyncio
            asyncio.run(sm.transition(TaskState.COMPLETED, trigger="bad"))


class TestSessionStatusMapping:
    """All TaskState values map correctly to SessionStatus."""

    def test_pending_maps_to_pending(self):
        assert to_session_status(TaskState.PENDING) == SessionStatus.PENDING

    def test_processing_maps_to_running(self):
        assert to_session_status(TaskState.PROCESSING) == SessionStatus.RUNNING

    def test_retrying_maps_to_running(self):
        assert to_session_status(TaskState.RETRYING) == SessionStatus.RUNNING

    def test_paused_maps_to_paused(self):
        assert to_session_status(TaskState.PAUSED) == SessionStatus.PAUSED

    def test_completed_maps_to_completed(self):
        assert to_session_status(TaskState.COMPLETED) == SessionStatus.COMPLETED

    def test_failed_maps_to_failed(self):
        assert to_session_status(TaskState.FAILED) == SessionStatus.FAILED

    def test_cancelled_maps_to_stopped(self):
        assert to_session_status(TaskState.CANCELLED) == SessionStatus.STOPPED

    def test_all_states_have_mapping(self):
        for state in TaskState:
            result = to_session_status(state)
            assert isinstance(result, SessionStatus), f"{state} not mapped"

    def test_session_status_enum_unchanged(self):
        values = {s.value for s in SessionStatus}
        assert values == {"pending", "running", "paused", "completed", "failed", "stopped"}


class TestProtocolClasses:
    """Protocol classes exist and have expected methods."""

    def test_memory_backend_protocol_exists(self):
        from app.core.protocols import MemoryBackend
        assert hasattr(MemoryBackend, "search")
        assert hasattr(MemoryBackend, "add")
        assert hasattr(MemoryBackend, "delete")

    def test_checkpoint_store_protocol_exists(self):
        from app.core.protocols import CheckpointStore
        assert hasattr(CheckpointStore, "save")
        assert hasattr(CheckpointStore, "load")
        assert hasattr(CheckpointStore, "list")

    def test_tool_executor_protocol_exists(self):
        from app.core.protocols import ToolExecutor
        assert hasattr(ToolExecutor, "execute")
        assert hasattr(ToolExecutor, "validate")

    def test_model_provider_protocol_exists(self):
        from app.core.protocols import ModelProvider
        assert hasattr(ModelProvider, "chat")
        assert hasattr(ModelProvider, "stream")

    def test_protocols_are_protocol_type(self):
        from typing import Protocol
        from app.core.protocols import MemoryBackend, CheckpointStore, ToolExecutor, ModelProvider
        assert issubclass(MemoryBackend, Protocol)
        assert issubclass(CheckpointStore, Protocol)
        assert issubclass(ToolExecutor, Protocol)
        assert issubclass(ModelProvider, Protocol)

"""Tests for custom exceptions."""

from __future__ import annotations

import pytest

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


class TestAgentEngineError:
    """Tests for base exception."""

    def test_can_be_raised(self):
        with pytest.raises(AgentEngineError):
            raise AgentEngineError("test error")

    def test_message_preserved(self):
        with pytest.raises(AgentEngineError, match="test message"):
            raise AgentEngineError("test message")


class TestSessionNotFoundError:
    """Tests for SessionNotFoundError."""

    def test_is_agent_engine_error(self):
        assert issubclass(SessionNotFoundError, AgentEngineError)

    def test_can_be_raised(self):
        with pytest.raises(SessionNotFoundError):
            raise SessionNotFoundError("session not found")


class TestInvalidStateTransitionError:
    """Tests for InvalidStateTransitionError."""

    def test_is_agent_engine_error(self):
        assert issubclass(InvalidStateTransitionError, AgentEngineError)

    def test_can_be_raised(self):
        with pytest.raises(InvalidStateTransitionError):
            raise InvalidStateTransitionError("invalid transition")


class TestToolExecutionError:
    """Tests for ToolExecutionError."""

    def test_is_agent_engine_error(self):
        assert issubclass(ToolExecutionError, AgentEngineError)

    def test_stores_tool_name(self):
        err = ToolExecutionError("echo", "execution failed")
        assert err.tool_name == "echo"

    def test_stores_details(self):
        err = ToolExecutionError("echo", "execution failed")
        assert err.details == "execution failed"

    def test_message_format(self):
        err = ToolExecutionError("echo", "execution failed")
        assert "echo" in str(err)
        assert "execution failed" in str(err)

    def test_empty_details(self):
        err = ToolExecutionError("echo")
        assert err.details == ""


class TestMemoryRetrievalError:
    """Tests for MemoryRetrievalError."""

    def test_is_agent_engine_error(self):
        assert issubclass(MemoryRetrievalError, AgentEngineError)

    def test_can_be_raised(self):
        with pytest.raises(MemoryRetrievalError):
            raise MemoryRetrievalError("memory retrieval failed")


class TestSecurityViolationError:
    """Tests for SecurityViolationError."""

    def test_is_agent_engine_error(self):
        assert issubclass(SecurityViolationError, AgentEngineError)

    def test_stores_violation_type(self):
        err = SecurityViolationError("xss", "malicious input detected")
        assert err.violation_type == "xss"

    def test_message_format(self):
        err = SecurityViolationError("xss", "malicious input detected")
        assert "xss" in str(err)
        assert "malicious input detected" in str(err)

    def test_empty_detail(self):
        err = SecurityViolationError("xss")
        assert "xss" in str(err)


class TestSubagentError:
    """Tests for SubagentError."""

    def test_is_agent_engine_error(self):
        assert issubclass(SubagentError, AgentEngineError)

    def test_stores_subagent_id(self):
        err = SubagentError("sub-1", 2, "error occurred")
        assert err.subagent_id == "sub-1"

    def test_stores_depth(self):
        err = SubagentError("sub-1", 3, "error occurred")
        assert err.depth == 3

    def test_message_format(self):
        err = SubagentError("sub-1", 2, "error occurred")
        assert "sub-1" in str(err)
        assert "depth 2" in str(err)


class TestPipelineError:
    """Tests for PipelineError."""

    def test_is_agent_engine_error(self):
        assert issubclass(PipelineError, AgentEngineError)

    def test_stores_step_name(self):
        err = PipelineError("step_1", "step failed")
        assert err.step_name == "step_1"

    def test_message_format(self):
        err = PipelineError("step_1", "step failed")
        assert "step_1" in str(err)
        assert "step failed" in str(err)


class TestEnsembleError:
    """Tests for EnsembleError."""

    def test_is_agent_engine_error(self):
        assert issubclass(EnsembleError, AgentEngineError)

    def test_stores_model_ids(self):
        err = EnsembleError(["gpt-4", "claude"], "ensemble failed")
        assert err.model_ids == ["gpt-4", "claude"]

    def test_message_format(self):
        err = EnsembleError(["gpt-4", "claude"], "ensemble failed")
        assert "gpt-4" in str(err)
        assert "claude" in str(err)


class TestExceptionHierarchy:
    """Tests for exception hierarchy."""

    def test_all_inherit_from_base(self):
        exceptions = [
            SessionNotFoundError,
            InvalidStateTransitionError,
            ToolExecutionError,
            MemoryRetrievalError,
            SecurityViolationError,
            SubagentError,
            PipelineError,
            EnsembleError,
        ]
        for exc_cls in exceptions:
            assert issubclass(exc_cls, AgentEngineError)

    def test_catch_all_with_base(self):
        with pytest.raises(AgentEngineError):
            raise ToolExecutionError("echo", "failed")

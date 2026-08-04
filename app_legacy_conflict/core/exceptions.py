"""Global exception hierarchy for the agent engine.

All custom exceptions inherit from AgentEngineError, enabling callers to
catch any engine-specific error with a single except clause.
"""

from __future__ import annotations


class AgentEngineError(Exception):
    """Base exception for all agent engine errors."""


class SessionNotFoundError(AgentEngineError):
    """Raised when a session ID does not exist."""


class InvalidStateTransitionError(AgentEngineError):
    """Raised when an invalid state transition is attempted."""


class ToolExecutionError(AgentEngineError):
    """Raised when a tool fails during execution."""

    def __init__(self, tool_name: str, details: str = "") -> None:
        super().__init__(f"Tool '{tool_name}' execution failed: {details}")
        self.tool_name = tool_name
        self.details = details


class MemoryRetrievalError(AgentEngineError):
    """Raised when memory retrieval fails."""


class SecurityViolationError(AgentEngineError):
    """Raised when a security policy is violated."""

    def __init__(self, violation_type: str, detail: str = "") -> None:
        super().__init__(f"Security violation ({violation_type}): {detail}")
        self.violation_type = violation_type


class SubagentError(AgentEngineError):
    """Raised when a sub-agent encounters an error."""

    def __init__(self, subagent_id: str, depth: int, detail: str = "") -> None:
        super().__init__(f"Subagent '{subagent_id}' (depth {depth}) error: {detail}")
        self.subagent_id = subagent_id
        self.depth = depth


class PipelineError(AgentEngineError):
    """Raised when a pipeline step fails."""

    def __init__(self, step_name: str, detail: str = "") -> None:
        super().__init__(f"Pipeline failed at [{step_name}]: {detail}")
        self.step_name = step_name


class EnsembleError(AgentEngineError):
    """Raised when ensemble execution fails."""

    def __init__(self, model_ids: list[str], detail: str = "") -> None:
        super().__init__(f"Ensemble error for models {model_ids}: {detail}")
        self.model_ids = model_ids

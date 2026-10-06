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


class BaseAppException(Exception):
    """Base class for API-facing exceptions handled by the global handler.

    Attributes:
        status_code: The HTTP status code to return for this error.
        error_type: A machine-readable error category exposed in the
            response body's `type` field.
        detail: Human-readable message exposed in the response body's
            `detail` field.
    """

    status_code: int = 500
    error_type: str = "internal_error"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFoundException(BaseAppException):
    """Raised when a requested resource does not exist."""

    status_code = 404
    error_type = "not_found"


class ValidationException(BaseAppException):
    """Raised when request data fails domain-level validation."""

    status_code = 422
    error_type = "validation_error"


class ConflictException(BaseAppException):
    """Raised when a request conflicts with existing resource state."""

    status_code = 409
    error_type = "conflict"


class AgentEngineHTTPError(BaseAppException, AgentEngineError):
    """HTTP-safe bridge between the API and agent engine exception trees.

    Raisers can use this when an engine failure should become a structured API
    response instead of being handled as an incidental unhandled exception.
    """

    status_code = 500
    error_type = "agent_engine_error"

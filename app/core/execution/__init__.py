"""Execution layer — task model, event-driven execution, HITL, circuit breaker.

AGI P3: Provides structured task execution with event-driven architecture,
human-in-the-loop approval, timeout enforcement, and circuit breaker protection.
"""

from app.core.execution.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerState,
    TimeoutManager,
)
from app.core.execution.engine import (
    TaskExecutionEngine,
)
from app.core.execution.event_bus import (
    EventBus,
    TaskEvent,
)
from app.core.execution.hitl import (
    HITLManager,
    HITLRequest,
    HITLStatusApproved,
    HITLStatusExpired,
    HITLStatusPending,
    HITLStatusRejected,
)
from app.core.execution.task_model import (
    SubTask,
    Task,
    TaskStore,
)

__all__ = [
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerState",
    "EventBus",
    "HITLManager",
    # HITL
    "HITLRequest",
    "HITLStatusApproved",
    "HITLStatusExpired",
    "HITLStatusPending",
    "HITLStatusRejected",
    "SubTask",
    # Task Model
    "Task",
    # Event Bus
    "TaskEvent",
    # Engine
    "TaskExecutionEngine",
    "TaskStore",
    "TimeoutManager",
]

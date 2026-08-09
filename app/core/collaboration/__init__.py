"""AGI P6 Collaboration Layer.

Provides A2A-compatible agent communication, task handoff,
role-based capability boundaries, and multi-agent result aggregation.
"""

from app.core.collaboration.a2a_protocol import (
    A2AMessage,
    A2AProtocol,
    A2AMessageType,
)
from app.core.collaboration.handoff import (
    HandoffManager,
    HandoffRequest,
    HandoffStatus,
)
from app.core.collaboration.roles import (
    AgentRole,
    Capability,
    RoleRegistry,
)
from app.core.collaboration.aggregation import (
    AgentResult,
    AggregationStrategy,
    ResultAggregator,
)

__all__ = [
    # A2A Protocol
    "A2AMessage",
    "A2AProtocol",
    "A2AMessageType",
    # Handoff
    "HandoffManager",
    "HandoffRequest",
    "HandoffStatus",
    # Roles
    "AgentRole",
    "Capability",
    "RoleRegistry",
    # Aggregation
    "AgentResult",
    "AggregationStrategy",
    "ResultAggregator",
]

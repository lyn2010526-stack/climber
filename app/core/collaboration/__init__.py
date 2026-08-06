"""Group collaboration engine modules.

Provides multi-agent collaboration capabilities including A2A protocol,
task handoff management, role-based capabilities, result aggregation,
and group orchestration.
"""

from app.core.collaboration.a2a_protocol import (
    A2AMessage,
    A2AMessageType,
    A2AProtocol,
)
from app.core.collaboration.aggregation import (
    AgentResult,
    AggregationStrategy,
    ResultAggregator,
)
from app.core.collaboration.base import (
    CollaborationResult,
    CollaborationTask,
    GroupCollaborationEngine,
    get_group_collaboration_engine,
)
from app.core.collaboration.handoff import (
    AgentCapability,
    HandoffManager,
    HandoffRequest,
    HandoffStatus,
)
from app.core.collaboration.roles import (
    AgentRole,
    Capability,
    RoleDefinition,
    RoleRegistry,
)

__all__ = [
    # A2A Protocol
    "A2AMessage",
    "A2AMessageType",
    "A2AProtocol",
    # Aggregation
    "AgentResult",
    "AggregationStrategy",
    "ResultAggregator",
    # Base Engine
    "CollaborationResult",
    "CollaborationTask",
    "GroupCollaborationEngine",
    "get_group_collaboration_engine",
    # Handoff
    "AgentCapability",
    "HandoffManager",
    "HandoffRequest",
    "HandoffStatus",
    # Roles
    "AgentRole",
    "Capability",
    "RoleDefinition",
    "RoleRegistry",
]

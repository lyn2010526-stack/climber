"""Observability subpackage — trace, audit, alignment, emergency stop.

AGI P4: Provides full trace tracking across all agent operations,
decision audit chain for compliance, goal alignment verification,
and global emergency stop capability.
"""

from app.core.observability.alignment import (
    AlignmentCheck,
    Goal,
    GoalTracker,
)
from app.core.observability.audit import (
    AuditChain,
    AuditEntry,
)
from app.core.observability.emergency_stop import (
    EmergencyStopManager,
    EmergencyStopRecord,
)
from app.core.observability.trace import (
    TraceCollector,
    TraceSpan,
)

__all__ = [
    # Alignment
    "AlignmentCheck",
    "AuditChain",
    # Audit
    "AuditEntry",
    # Emergency Stop
    "EmergencyStopManager",
    "EmergencyStopRecord",
    "Goal",
    "GoalTracker",
    "TraceCollector",
    # Trace
    "TraceSpan",
]

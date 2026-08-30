"""Mixed capability integration + event-sourcing state layer.

9.1  kernel stays minimal: event bus + graph executor + protocol router.
9.6  event sourcing: every state is a projection of the event stream. The
     conversation is a projection of message events, the skill library is a
     projection of skill create/update events, stats are aggregation
     projections, and the UI is a live projection. Replaying the stream
     rebuilds any state (time travel).
"""

from app.core.integration.event_sourcing import (
    EventSourcedStore,
    EventSourcingManager,
)
from app.core.integration.event_store import EventStore
from app.core.integration.protocol_router import (
    ProtocolRouter,
    get_protocol_router,
)

__all__ = [
    "EventSourcedStore",
    "EventSourcingManager",
    "EventStore",
    "ProtocolRouter",
    "get_protocol_router",
]

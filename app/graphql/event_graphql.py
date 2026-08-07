"""GraphQL: event - GraphQL schema and resolvers."""

from __future__ import annotations

from datetime import datetime

import strawberry


@strawberry.type
class EventType:
    """GraphQL type."""
    id: int = 0
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'
    created_at: datetime = strawberry.field(default_factory=datetime.utcnow)
    updated_at: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type
class EventConnection:
    """Connection type."""
    items: list[EventType] = strawberry.field(default_factory=list)
    total: int = 0
    has_next_page: bool = False
    has_previous_page: bool = False


@strawberry.input
class EventCreateInput:
    """Create input."""
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'


@strawberry.input
class EventUpdateInput:
    """Update input."""
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.input
class EventFilterInput:
    """Filter input."""
    search: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.type
class EventMutations:
    """Mutations."""

    @strawberry.mutation
    async def create_event(self, input: EventCreateInput) -> EventType:
        """Create mutation."""
        return EventType(
            id=1,
            name=input.name,
            description=input.description,
            status=input.status,
            priority=input.priority,
        )

    @strawberry.mutation
    async def update_event(self, id: int, input: EventUpdateInput) -> EventType | None:
        """Update mutation."""
        return EventType(
            id=id,
            name=input.name or 'updated',
            description=input.description or '',
            status=input.status or 'active',
            priority=input.priority or 'medium',
        )

    @strawberry.mutation
    async def delete_event(self, id: int) -> bool:
        """Delete mutation."""
        return True


@strawberry.type
class EventQueries:
    """Queries."""

    @strawberry.field
    async def event(self, id: int) -> EventType | None:
        """Get by ID."""
        return EventType(id=id, name='Test')

    @strawberry.field
    async def events(
        self,
        filter: EventFilterInput | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> EventConnection:
        """List query."""
        items = [EventType(id=i, name=f'Item {i}') for i in range(limit)]
        return EventConnection(items=items, total=limit)


def create_event_schema() -> strawberry.Schema:
    """Create schema."""
    return strawberry.Schema(query=EventQueries, mutation=EventMutations)

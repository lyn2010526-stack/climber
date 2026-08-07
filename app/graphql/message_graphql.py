"""GraphQL: message - GraphQL schema and resolvers."""

from __future__ import annotations

from datetime import datetime

import strawberry


@strawberry.type
class MessageType:
    """GraphQL type."""
    id: int = 0
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'
    created_at: datetime = strawberry.field(default_factory=datetime.utcnow)
    updated_at: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type
class MessageConnection:
    """Connection type."""
    items: list[MessageType] = strawberry.field(default_factory=list)
    total: int = 0
    has_next_page: bool = False
    has_previous_page: bool = False


@strawberry.input
class MessageCreateInput:
    """Create input."""
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'


@strawberry.input
class MessageUpdateInput:
    """Update input."""
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.input
class MessageFilterInput:
    """Filter input."""
    search: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.type
class MessageMutations:
    """Mutations."""

    @strawberry.mutation
    async def create_message(self, input: MessageCreateInput) -> MessageType:
        """Create mutation."""
        return MessageType(
            id=1,
            name=input.name,
            description=input.description,
            status=input.status,
            priority=input.priority,
        )

    @strawberry.mutation
    async def update_message(self, id: int, input: MessageUpdateInput) -> MessageType | None:
        """Update mutation."""
        return MessageType(
            id=id,
            name=input.name or 'updated',
            description=input.description or '',
            status=input.status or 'active',
            priority=input.priority or 'medium',
        )

    @strawberry.mutation
    async def delete_message(self, id: int) -> bool:
        """Delete mutation."""
        return True


@strawberry.type
class MessageQueries:
    """Queries."""

    @strawberry.field
    async def message(self, id: int) -> MessageType | None:
        """Get by ID."""
        return MessageType(id=id, name='Test')

    @strawberry.field
    async def messages(
        self,
        filter: MessageFilterInput | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> MessageConnection:
        """List query."""
        items = [MessageType(id=i, name=f'Item {i}') for i in range(limit)]
        return MessageConnection(items=items, total=limit)


def create_message_schema() -> strawberry.Schema:
    """Create schema."""
    return strawberry.Schema(query=MessageQueries, mutation=MessageMutations)

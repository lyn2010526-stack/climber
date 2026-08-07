"""GraphQL: notification - GraphQL schema and resolvers."""

from __future__ import annotations

from datetime import datetime

import strawberry


@strawberry.type
class NotificationType:
    """GraphQL type."""
    id: int = 0
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'
    created_at: datetime = strawberry.field(default_factory=datetime.utcnow)
    updated_at: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type
class NotificationConnection:
    """Connection type."""
    items: list[NotificationType] = strawberry.field(default_factory=list)
    total: int = 0
    has_next_page: bool = False
    has_previous_page: bool = False


@strawberry.input
class NotificationCreateInput:
    """Create input."""
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'


@strawberry.input
class NotificationUpdateInput:
    """Update input."""
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.input
class NotificationFilterInput:
    """Filter input."""
    search: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.type
class NotificationMutations:
    """Mutations."""

    @strawberry.mutation
    async def create_notification(self, input: NotificationCreateInput) -> NotificationType:
        """Create mutation."""
        return NotificationType(
            id=1,
            name=input.name,
            description=input.description,
            status=input.status,
            priority=input.priority,
        )

    @strawberry.mutation
    async def update_notification(self, id: int, input: NotificationUpdateInput) -> NotificationType | None:
        """Update mutation."""
        return NotificationType(
            id=id,
            name=input.name or 'updated',
            description=input.description or '',
            status=input.status or 'active',
            priority=input.priority or 'medium',
        )

    @strawberry.mutation
    async def delete_notification(self, id: int) -> bool:
        """Delete mutation."""
        return True


@strawberry.type
class NotificationQueries:
    """Queries."""

    @strawberry.field
    async def notification(self, id: int) -> NotificationType | None:
        """Get by ID."""
        return NotificationType(id=id, name='Test')

    @strawberry.field
    async def notifications(
        self,
        filter: NotificationFilterInput | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> NotificationConnection:
        """List query."""
        items = [NotificationType(id=i, name=f'Item {i}') for i in range(limit)]
        return NotificationConnection(items=items, total=limit)


def create_notification_schema() -> strawberry.Schema:
    """Create schema."""
    return strawberry.Schema(query=NotificationQueries, mutation=NotificationMutations)

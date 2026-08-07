"""GraphQL: widget - GraphQL schema and resolvers."""

from __future__ import annotations

from datetime import datetime

import strawberry


@strawberry.type
class WidgetType:
    """GraphQL type."""
    id: int = 0
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'
    created_at: datetime = strawberry.field(default_factory=datetime.utcnow)
    updated_at: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type
class WidgetConnection:
    """Connection type."""
    items: list[WidgetType] = strawberry.field(default_factory=list)
    total: int = 0
    has_next_page: bool = False
    has_previous_page: bool = False


@strawberry.input
class WidgetCreateInput:
    """Create input."""
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'


@strawberry.input
class WidgetUpdateInput:
    """Update input."""
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.input
class WidgetFilterInput:
    """Filter input."""
    search: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.type
class WidgetMutations:
    """Mutations."""

    @strawberry.mutation
    async def create_widget(self, input: WidgetCreateInput) -> WidgetType:
        """Create mutation."""
        return WidgetType(
            id=1,
            name=input.name,
            description=input.description,
            status=input.status,
            priority=input.priority,
        )

    @strawberry.mutation
    async def update_widget(self, id: int, input: WidgetUpdateInput) -> WidgetType | None:
        """Update mutation."""
        return WidgetType(
            id=id,
            name=input.name or 'updated',
            description=input.description or '',
            status=input.status or 'active',
            priority=input.priority or 'medium',
        )

    @strawberry.mutation
    async def delete_widget(self, id: int) -> bool:
        """Delete mutation."""
        return True


@strawberry.type
class WidgetQueries:
    """Queries."""

    @strawberry.field
    async def widget(self, id: int) -> WidgetType | None:
        """Get by ID."""
        return WidgetType(id=id, name='Test')

    @strawberry.field
    async def widgets(
        self,
        filter: WidgetFilterInput | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> WidgetConnection:
        """List query."""
        items = [WidgetType(id=i, name=f'Item {i}') for i in range(limit)]
        return WidgetConnection(items=items, total=limit)


def create_widget_schema() -> strawberry.Schema:
    """Create schema."""
    return strawberry.Schema(query=WidgetQueries, mutation=WidgetMutations)

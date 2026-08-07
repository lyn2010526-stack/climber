"""GraphQL: chart - GraphQL schema and resolvers."""

from __future__ import annotations

from datetime import datetime

import strawberry


@strawberry.type
class ChartType:
    """GraphQL type."""
    id: int = 0
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'
    created_at: datetime = strawberry.field(default_factory=datetime.utcnow)
    updated_at: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type
class ChartConnection:
    """Connection type."""
    items: list[ChartType] = strawberry.field(default_factory=list)
    total: int = 0
    has_next_page: bool = False
    has_previous_page: bool = False


@strawberry.input
class ChartCreateInput:
    """Create input."""
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'


@strawberry.input
class ChartUpdateInput:
    """Update input."""
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.input
class ChartFilterInput:
    """Filter input."""
    search: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.type
class ChartMutations:
    """Mutations."""

    @strawberry.mutation
    async def create_chart(self, input: ChartCreateInput) -> ChartType:
        """Create mutation."""
        return ChartType(
            id=1,
            name=input.name,
            description=input.description,
            status=input.status,
            priority=input.priority,
        )

    @strawberry.mutation
    async def update_chart(self, id: int, input: ChartUpdateInput) -> ChartType | None:
        """Update mutation."""
        return ChartType(
            id=id,
            name=input.name or 'updated',
            description=input.description or '',
            status=input.status or 'active',
            priority=input.priority or 'medium',
        )

    @strawberry.mutation
    async def delete_chart(self, id: int) -> bool:
        """Delete mutation."""
        return True


@strawberry.type
class ChartQueries:
    """Queries."""

    @strawberry.field
    async def chart(self, id: int) -> ChartType | None:
        """Get by ID."""
        return ChartType(id=id, name='Test')

    @strawberry.field
    async def charts(
        self,
        filter: ChartFilterInput | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ChartConnection:
        """List query."""
        items = [ChartType(id=i, name=f'Item {i}') for i in range(limit)]
        return ChartConnection(items=items, total=limit)


def create_chart_schema() -> strawberry.Schema:
    """Create schema."""
    return strawberry.Schema(query=ChartQueries, mutation=ChartMutations)

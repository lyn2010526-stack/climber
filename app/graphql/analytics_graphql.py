"""GraphQL: analytics - GraphQL schema and resolvers."""

from __future__ import annotations

from datetime import datetime

import strawberry


@strawberry.type
class AnalyticsType:
    """GraphQL type."""
    id: int = 0
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'
    created_at: datetime = strawberry.field(default_factory=datetime.utcnow)
    updated_at: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type
class AnalyticsConnection:
    """Connection type."""
    items: list[AnalyticsType] = strawberry.field(default_factory=list)
    total: int = 0
    has_next_page: bool = False
    has_previous_page: bool = False


@strawberry.input
class AnalyticsCreateInput:
    """Create input."""
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'


@strawberry.input
class AnalyticsUpdateInput:
    """Update input."""
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.input
class AnalyticsFilterInput:
    """Filter input."""
    search: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.type
class AnalyticsMutations:
    """Mutations."""

    @strawberry.mutation
    async def create_analytics(self, input: AnalyticsCreateInput) -> AnalyticsType:
        """Create mutation."""
        return AnalyticsType(
            id=1,
            name=input.name,
            description=input.description,
            status=input.status,
            priority=input.priority,
        )

    @strawberry.mutation
    async def update_analytics(self, id: int, input: AnalyticsUpdateInput) -> AnalyticsType | None:
        """Update mutation."""
        return AnalyticsType(
            id=id,
            name=input.name or 'updated',
            description=input.description or '',
            status=input.status or 'active',
            priority=input.priority or 'medium',
        )

    @strawberry.mutation
    async def delete_analytics(self, id: int) -> bool:
        """Delete mutation."""
        return True


@strawberry.type
class AnalyticsQueries:
    """Queries."""

    @strawberry.field
    async def analytics(self, id: int) -> AnalyticsType | None:
        """Get by ID."""
        return AnalyticsType(id=id, name='Test')

    @strawberry.field
    async def analyticss(
        self,
        filter: AnalyticsFilterInput | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> AnalyticsConnection:
        """List query."""
        items = [AnalyticsType(id=i, name=f'Item {i}') for i in range(limit)]
        return AnalyticsConnection(items=items, total=limit)


def create_analytics_schema() -> strawberry.Schema:
    """Create schema."""
    return strawberry.Schema(query=AnalyticsQueries, mutation=AnalyticsMutations)

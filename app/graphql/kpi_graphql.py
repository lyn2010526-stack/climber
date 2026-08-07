"""GraphQL: kpi - GraphQL schema and resolvers."""

from __future__ import annotations

from datetime import datetime

import strawberry


@strawberry.type
class KpiType:
    """GraphQL type."""
    id: int = 0
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'
    created_at: datetime = strawberry.field(default_factory=datetime.utcnow)
    updated_at: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type
class KpiConnection:
    """Connection type."""
    items: list[KpiType] = strawberry.field(default_factory=list)
    total: int = 0
    has_next_page: bool = False
    has_previous_page: bool = False


@strawberry.input
class KpiCreateInput:
    """Create input."""
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'


@strawberry.input
class KpiUpdateInput:
    """Update input."""
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.input
class KpiFilterInput:
    """Filter input."""
    search: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.type
class KpiMutations:
    """Mutations."""

    @strawberry.mutation
    async def create_kpi(self, input: KpiCreateInput) -> KpiType:
        """Create mutation."""
        return KpiType(
            id=1,
            name=input.name,
            description=input.description,
            status=input.status,
            priority=input.priority,
        )

    @strawberry.mutation
    async def update_kpi(self, id: int, input: KpiUpdateInput) -> KpiType | None:
        """Update mutation."""
        return KpiType(
            id=id,
            name=input.name or 'updated',
            description=input.description or '',
            status=input.status or 'active',
            priority=input.priority or 'medium',
        )

    @strawberry.mutation
    async def delete_kpi(self, id: int) -> bool:
        """Delete mutation."""
        return True


@strawberry.type
class KpiQueries:
    """Queries."""

    @strawberry.field
    async def kpi(self, id: int) -> KpiType | None:
        """Get by ID."""
        return KpiType(id=id, name='Test')

    @strawberry.field
    async def kpis(
        self,
        filter: KpiFilterInput | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> KpiConnection:
        """List query."""
        items = [KpiType(id=i, name=f'Item {i}') for i in range(limit)]
        return KpiConnection(items=items, total=limit)


def create_kpi_schema() -> strawberry.Schema:
    """Create schema."""
    return strawberry.Schema(query=KpiQueries, mutation=KpiMutations)

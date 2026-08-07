"""GraphQL: dashboard - GraphQL schema and resolvers."""

from __future__ import annotations

from datetime import datetime

import strawberry


@strawberry.type
class DashboardType:
    """GraphQL type."""
    id: int = 0
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'
    created_at: datetime = strawberry.field(default_factory=datetime.utcnow)
    updated_at: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type
class DashboardConnection:
    """Connection type."""
    items: list[DashboardType] = strawberry.field(default_factory=list)
    total: int = 0
    has_next_page: bool = False
    has_previous_page: bool = False


@strawberry.input
class DashboardCreateInput:
    """Create input."""
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'


@strawberry.input
class DashboardUpdateInput:
    """Update input."""
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.input
class DashboardFilterInput:
    """Filter input."""
    search: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.type
class DashboardMutations:
    """Mutations."""

    @strawberry.mutation
    async def create_dashboard(self, input: DashboardCreateInput) -> DashboardType:
        """Create mutation."""
        return DashboardType(
            id=1,
            name=input.name,
            description=input.description,
            status=input.status,
            priority=input.priority,
        )

    @strawberry.mutation
    async def update_dashboard(self, id: int, input: DashboardUpdateInput) -> DashboardType | None:
        """Update mutation."""
        return DashboardType(
            id=id,
            name=input.name or 'updated',
            description=input.description or '',
            status=input.status or 'active',
            priority=input.priority or 'medium',
        )

    @strawberry.mutation
    async def delete_dashboard(self, id: int) -> bool:
        """Delete mutation."""
        return True


@strawberry.type
class DashboardQueries:
    """Queries."""

    @strawberry.field
    async def dashboard(self, id: int) -> DashboardType | None:
        """Get by ID."""
        return DashboardType(id=id, name='Test')

    @strawberry.field
    async def dashboards(
        self,
        filter: DashboardFilterInput | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> DashboardConnection:
        """List query."""
        items = [DashboardType(id=i, name=f'Item {i}') for i in range(limit)]
        return DashboardConnection(items=items, total=limit)


def create_dashboard_schema() -> strawberry.Schema:
    """Create schema."""
    return strawberry.Schema(query=DashboardQueries, mutation=DashboardMutations)

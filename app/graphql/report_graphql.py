"""GraphQL: report - GraphQL schema and resolvers."""

from __future__ import annotations

from datetime import datetime

import strawberry


@strawberry.type
class ReportType:
    """GraphQL type."""
    id: int = 0
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'
    created_at: datetime = strawberry.field(default_factory=datetime.utcnow)
    updated_at: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type
class ReportConnection:
    """Connection type."""
    items: list[ReportType] = strawberry.field(default_factory=list)
    total: int = 0
    has_next_page: bool = False
    has_previous_page: bool = False


@strawberry.input
class ReportCreateInput:
    """Create input."""
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'


@strawberry.input
class ReportUpdateInput:
    """Update input."""
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.input
class ReportFilterInput:
    """Filter input."""
    search: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.type
class ReportMutations:
    """Mutations."""

    @strawberry.mutation
    async def create_report(self, input: ReportCreateInput) -> ReportType:
        """Create mutation."""
        return ReportType(
            id=1,
            name=input.name,
            description=input.description,
            status=input.status,
            priority=input.priority,
        )

    @strawberry.mutation
    async def update_report(self, id: int, input: ReportUpdateInput) -> ReportType | None:
        """Update mutation."""
        return ReportType(
            id=id,
            name=input.name or 'updated',
            description=input.description or '',
            status=input.status or 'active',
            priority=input.priority or 'medium',
        )

    @strawberry.mutation
    async def delete_report(self, id: int) -> bool:
        """Delete mutation."""
        return True


@strawberry.type
class ReportQueries:
    """Queries."""

    @strawberry.field
    async def report(self, id: int) -> ReportType | None:
        """Get by ID."""
        return ReportType(id=id, name='Test')

    @strawberry.field
    async def reports(
        self,
        filter: ReportFilterInput | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ReportConnection:
        """List query."""
        items = [ReportType(id=i, name=f'Item {i}') for i in range(limit)]
        return ReportConnection(items=items, total=limit)


def create_report_schema() -> strawberry.Schema:
    """Create schema."""
    return strawberry.Schema(query=ReportQueries, mutation=ReportMutations)

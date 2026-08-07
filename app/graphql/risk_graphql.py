"""GraphQL: risk - GraphQL schema and resolvers."""

from __future__ import annotations

from datetime import datetime

import strawberry


@strawberry.type
class RiskType:
    """GraphQL type."""
    id: int = 0
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'
    created_at: datetime = strawberry.field(default_factory=datetime.utcnow)
    updated_at: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type
class RiskConnection:
    """Connection type."""
    items: list[RiskType] = strawberry.field(default_factory=list)
    total: int = 0
    has_next_page: bool = False
    has_previous_page: bool = False


@strawberry.input
class RiskCreateInput:
    """Create input."""
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'


@strawberry.input
class RiskUpdateInput:
    """Update input."""
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.input
class RiskFilterInput:
    """Filter input."""
    search: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.type
class RiskMutations:
    """Mutations."""

    @strawberry.mutation
    async def create_risk(self, input: RiskCreateInput) -> RiskType:
        """Create mutation."""
        return RiskType(
            id=1,
            name=input.name,
            description=input.description,
            status=input.status,
            priority=input.priority,
        )

    @strawberry.mutation
    async def update_risk(self, id: int, input: RiskUpdateInput) -> RiskType | None:
        """Update mutation."""
        return RiskType(
            id=id,
            name=input.name or 'updated',
            description=input.description or '',
            status=input.status or 'active',
            priority=input.priority or 'medium',
        )

    @strawberry.mutation
    async def delete_risk(self, id: int) -> bool:
        """Delete mutation."""
        return True


@strawberry.type
class RiskQueries:
    """Queries."""

    @strawberry.field
    async def risk(self, id: int) -> RiskType | None:
        """Get by ID."""
        return RiskType(id=id, name='Test')

    @strawberry.field
    async def risks(
        self,
        filter: RiskFilterInput | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> RiskConnection:
        """List query."""
        items = [RiskType(id=i, name=f'Item {i}') for i in range(limit)]
        return RiskConnection(items=items, total=limit)


def create_risk_schema() -> strawberry.Schema:
    """Create schema."""
    return strawberry.Schema(query=RiskQueries, mutation=RiskMutations)

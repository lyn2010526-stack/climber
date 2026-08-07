"""GraphQL: initiative - GraphQL schema and resolvers."""

from __future__ import annotations

from datetime import datetime

import strawberry


@strawberry.type
class InitiativeType:
    """GraphQL type."""
    id: int = 0
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'
    created_at: datetime = strawberry.field(default_factory=datetime.utcnow)
    updated_at: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type
class InitiativeConnection:
    """Connection type."""
    items: list[InitiativeType] = strawberry.field(default_factory=list)
    total: int = 0
    has_next_page: bool = False
    has_previous_page: bool = False


@strawberry.input
class InitiativeCreateInput:
    """Create input."""
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'


@strawberry.input
class InitiativeUpdateInput:
    """Update input."""
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.input
class InitiativeFilterInput:
    """Filter input."""
    search: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.type
class InitiativeMutations:
    """Mutations."""

    @strawberry.mutation
    async def create_initiative(self, input: InitiativeCreateInput) -> InitiativeType:
        """Create mutation."""
        return InitiativeType(
            id=1,
            name=input.name,
            description=input.description,
            status=input.status,
            priority=input.priority,
        )

    @strawberry.mutation
    async def update_initiative(self, id: int, input: InitiativeUpdateInput) -> InitiativeType | None:
        """Update mutation."""
        return InitiativeType(
            id=id,
            name=input.name or 'updated',
            description=input.description or '',
            status=input.status or 'active',
            priority=input.priority or 'medium',
        )

    @strawberry.mutation
    async def delete_initiative(self, id: int) -> bool:
        """Delete mutation."""
        return True


@strawberry.type
class InitiativeQueries:
    """Queries."""

    @strawberry.field
    async def initiative(self, id: int) -> InitiativeType | None:
        """Get by ID."""
        return InitiativeType(id=id, name='Test')

    @strawberry.field
    async def initiatives(
        self,
        filter: InitiativeFilterInput | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> InitiativeConnection:
        """List query."""
        items = [InitiativeType(id=i, name=f'Item {i}') for i in range(limit)]
        return InitiativeConnection(items=items, total=limit)


def create_initiative_schema() -> strawberry.Schema:
    """Create schema."""
    return strawberry.Schema(query=InitiativeQueries, mutation=InitiativeMutations)

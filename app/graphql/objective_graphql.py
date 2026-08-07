"""GraphQL: objective - GraphQL schema and resolvers."""

from __future__ import annotations

from datetime import datetime

import strawberry


@strawberry.type
class ObjectiveType:
    """GraphQL type."""
    id: int = 0
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'
    created_at: datetime = strawberry.field(default_factory=datetime.utcnow)
    updated_at: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type
class ObjectiveConnection:
    """Connection type."""
    items: list[ObjectiveType] = strawberry.field(default_factory=list)
    total: int = 0
    has_next_page: bool = False
    has_previous_page: bool = False


@strawberry.input
class ObjectiveCreateInput:
    """Create input."""
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'


@strawberry.input
class ObjectiveUpdateInput:
    """Update input."""
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.input
class ObjectiveFilterInput:
    """Filter input."""
    search: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.type
class ObjectiveMutations:
    """Mutations."""

    @strawberry.mutation
    async def create_objective(self, input: ObjectiveCreateInput) -> ObjectiveType:
        """Create mutation."""
        return ObjectiveType(
            id=1,
            name=input.name,
            description=input.description,
            status=input.status,
            priority=input.priority,
        )

    @strawberry.mutation
    async def update_objective(self, id: int, input: ObjectiveUpdateInput) -> ObjectiveType | None:
        """Update mutation."""
        return ObjectiveType(
            id=id,
            name=input.name or 'updated',
            description=input.description or '',
            status=input.status or 'active',
            priority=input.priority or 'medium',
        )

    @strawberry.mutation
    async def delete_objective(self, id: int) -> bool:
        """Delete mutation."""
        return True


@strawberry.type
class ObjectiveQueries:
    """Queries."""

    @strawberry.field
    async def objective(self, id: int) -> ObjectiveType | None:
        """Get by ID."""
        return ObjectiveType(id=id, name='Test')

    @strawberry.field
    async def objectives(
        self,
        filter: ObjectiveFilterInput | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ObjectiveConnection:
        """List query."""
        items = [ObjectiveType(id=i, name=f'Item {i}') for i in range(limit)]
        return ObjectiveConnection(items=items, total=limit)


def create_objective_schema() -> strawberry.Schema:
    """Create schema."""
    return strawberry.Schema(query=ObjectiveQueries, mutation=ObjectiveMutations)

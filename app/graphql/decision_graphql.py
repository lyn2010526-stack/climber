"""GraphQL: decision - GraphQL schema and resolvers."""

from __future__ import annotations

from datetime import datetime

import strawberry


@strawberry.type
class DecisionType:
    """GraphQL type."""
    id: int = 0
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'
    created_at: datetime = strawberry.field(default_factory=datetime.utcnow)
    updated_at: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type
class DecisionConnection:
    """Connection type."""
    items: list[DecisionType] = strawberry.field(default_factory=list)
    total: int = 0
    has_next_page: bool = False
    has_previous_page: bool = False


@strawberry.input
class DecisionCreateInput:
    """Create input."""
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'


@strawberry.input
class DecisionUpdateInput:
    """Update input."""
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.input
class DecisionFilterInput:
    """Filter input."""
    search: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.type
class DecisionMutations:
    """Mutations."""

    @strawberry.mutation
    async def create_decision(self, input: DecisionCreateInput) -> DecisionType:
        """Create mutation."""
        return DecisionType(
            id=1,
            name=input.name,
            description=input.description,
            status=input.status,
            priority=input.priority,
        )

    @strawberry.mutation
    async def update_decision(self, id: int, input: DecisionUpdateInput) -> DecisionType | None:
        """Update mutation."""
        return DecisionType(
            id=id,
            name=input.name or 'updated',
            description=input.description or '',
            status=input.status or 'active',
            priority=input.priority or 'medium',
        )

    @strawberry.mutation
    async def delete_decision(self, id: int) -> bool:
        """Delete mutation."""
        return True


@strawberry.type
class DecisionQueries:
    """Queries."""

    @strawberry.field
    async def decision(self, id: int) -> DecisionType | None:
        """Get by ID."""
        return DecisionType(id=id, name='Test')

    @strawberry.field
    async def decisions(
        self,
        filter: DecisionFilterInput | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> DecisionConnection:
        """List query."""
        items = [DecisionType(id=i, name=f'Item {i}') for i in range(limit)]
        return DecisionConnection(items=items, total=limit)


def create_decision_schema() -> strawberry.Schema:
    """Create schema."""
    return strawberry.Schema(query=DecisionQueries, mutation=DecisionMutations)

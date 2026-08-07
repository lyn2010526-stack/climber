"""GraphQL: goal - GraphQL schema and resolvers."""

from __future__ import annotations

from datetime import datetime

import strawberry


@strawberry.type
class GoalType:
    """GraphQL type."""
    id: int = 0
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'
    created_at: datetime = strawberry.field(default_factory=datetime.utcnow)
    updated_at: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type
class GoalConnection:
    """Connection type."""
    items: list[GoalType] = strawberry.field(default_factory=list)
    total: int = 0
    has_next_page: bool = False
    has_previous_page: bool = False


@strawberry.input
class GoalCreateInput:
    """Create input."""
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'


@strawberry.input
class GoalUpdateInput:
    """Update input."""
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.input
class GoalFilterInput:
    """Filter input."""
    search: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.type
class GoalMutations:
    """Mutations."""

    @strawberry.mutation
    async def create_goal(self, input: GoalCreateInput) -> GoalType:
        """Create mutation."""
        return GoalType(
            id=1,
            name=input.name,
            description=input.description,
            status=input.status,
            priority=input.priority,
        )

    @strawberry.mutation
    async def update_goal(self, id: int, input: GoalUpdateInput) -> GoalType | None:
        """Update mutation."""
        return GoalType(
            id=id,
            name=input.name or 'updated',
            description=input.description or '',
            status=input.status or 'active',
            priority=input.priority or 'medium',
        )

    @strawberry.mutation
    async def delete_goal(self, id: int) -> bool:
        """Delete mutation."""
        return True


@strawberry.type
class GoalQueries:
    """Queries."""

    @strawberry.field
    async def goal(self, id: int) -> GoalType | None:
        """Get by ID."""
        return GoalType(id=id, name='Test')

    @strawberry.field
    async def goals(
        self,
        filter: GoalFilterInput | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> GoalConnection:
        """List query."""
        items = [GoalType(id=i, name=f'Item {i}') for i in range(limit)]
        return GoalConnection(items=items, total=limit)


def create_goal_schema() -> strawberry.Schema:
    """Create schema."""
    return strawberry.Schema(query=GoalQueries, mutation=GoalMutations)

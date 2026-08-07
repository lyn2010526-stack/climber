"""GraphQL: team - GraphQL schema and resolvers."""

from __future__ import annotations

from datetime import datetime

import strawberry


@strawberry.type
class TeamType:
    """GraphQL type."""
    id: int = 0
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'
    created_at: datetime = strawberry.field(default_factory=datetime.utcnow)
    updated_at: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type
class TeamConnection:
    """Connection type."""
    items: list[TeamType] = strawberry.field(default_factory=list)
    total: int = 0
    has_next_page: bool = False
    has_previous_page: bool = False


@strawberry.input
class TeamCreateInput:
    """Create input."""
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'


@strawberry.input
class TeamUpdateInput:
    """Update input."""
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.input
class TeamFilterInput:
    """Filter input."""
    search: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.type
class TeamMutations:
    """Mutations."""

    @strawberry.mutation
    async def create_team(self, input: TeamCreateInput) -> TeamType:
        """Create mutation."""
        return TeamType(
            id=1,
            name=input.name,
            description=input.description,
            status=input.status,
            priority=input.priority,
        )

    @strawberry.mutation
    async def update_team(self, id: int, input: TeamUpdateInput) -> TeamType | None:
        """Update mutation."""
        return TeamType(
            id=id,
            name=input.name or 'updated',
            description=input.description or '',
            status=input.status or 'active',
            priority=input.priority or 'medium',
        )

    @strawberry.mutation
    async def delete_team(self, id: int) -> bool:
        """Delete mutation."""
        return True


@strawberry.type
class TeamQueries:
    """Queries."""

    @strawberry.field
    async def team(self, id: int) -> TeamType | None:
        """Get by ID."""
        return TeamType(id=id, name='Test')

    @strawberry.field
    async def teams(
        self,
        filter: TeamFilterInput | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> TeamConnection:
        """List query."""
        items = [TeamType(id=i, name=f'Item {i}') for i in range(limit)]
        return TeamConnection(items=items, total=limit)


def create_team_schema() -> strawberry.Schema:
    """Create schema."""
    return strawberry.Schema(query=TeamQueries, mutation=TeamMutations)

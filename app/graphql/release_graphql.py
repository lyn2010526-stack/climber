"""GraphQL: release - GraphQL schema and resolvers."""

from __future__ import annotations

from datetime import datetime

import strawberry


@strawberry.type
class ReleaseType:
    """GraphQL type."""
    id: int = 0
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'
    created_at: datetime = strawberry.field(default_factory=datetime.utcnow)
    updated_at: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type
class ReleaseConnection:
    """Connection type."""
    items: list[ReleaseType] = strawberry.field(default_factory=list)
    total: int = 0
    has_next_page: bool = False
    has_previous_page: bool = False


@strawberry.input
class ReleaseCreateInput:
    """Create input."""
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'


@strawberry.input
class ReleaseUpdateInput:
    """Update input."""
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.input
class ReleaseFilterInput:
    """Filter input."""
    search: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.type
class ReleaseMutations:
    """Mutations."""

    @strawberry.mutation
    async def create_release(self, input: ReleaseCreateInput) -> ReleaseType:
        """Create mutation."""
        return ReleaseType(
            id=1,
            name=input.name,
            description=input.description,
            status=input.status,
            priority=input.priority,
        )

    @strawberry.mutation
    async def update_release(self, id: int, input: ReleaseUpdateInput) -> ReleaseType | None:
        """Update mutation."""
        return ReleaseType(
            id=id,
            name=input.name or 'updated',
            description=input.description or '',
            status=input.status or 'active',
            priority=input.priority or 'medium',
        )

    @strawberry.mutation
    async def delete_release(self, id: int) -> bool:
        """Delete mutation."""
        return True


@strawberry.type
class ReleaseQueries:
    """Queries."""

    @strawberry.field
    async def release(self, id: int) -> ReleaseType | None:
        """Get by ID."""
        return ReleaseType(id=id, name='Test')

    @strawberry.field
    async def releases(
        self,
        filter: ReleaseFilterInput | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ReleaseConnection:
        """List query."""
        items = [ReleaseType(id=i, name=f'Item {i}') for i in range(limit)]
        return ReleaseConnection(items=items, total=limit)


def create_release_schema() -> strawberry.Schema:
    """Create schema."""
    return strawberry.Schema(query=ReleaseQueries, mutation=ReleaseMutations)

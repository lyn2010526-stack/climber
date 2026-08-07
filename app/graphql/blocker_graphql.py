"""GraphQL: blocker - GraphQL schema and resolvers."""

from __future__ import annotations

from datetime import datetime

import strawberry


@strawberry.type
class BlockerType:
    """GraphQL type."""
    id: int = 0
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'
    created_at: datetime = strawberry.field(default_factory=datetime.utcnow)
    updated_at: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type
class BlockerConnection:
    """Connection type."""
    items: list[BlockerType] = strawberry.field(default_factory=list)
    total: int = 0
    has_next_page: bool = False
    has_previous_page: bool = False


@strawberry.input
class BlockerCreateInput:
    """Create input."""
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'


@strawberry.input
class BlockerUpdateInput:
    """Update input."""
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.input
class BlockerFilterInput:
    """Filter input."""
    search: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.type
class BlockerMutations:
    """Mutations."""

    @strawberry.mutation
    async def create_blocker(self, input: BlockerCreateInput) -> BlockerType:
        """Create mutation."""
        return BlockerType(
            id=1,
            name=input.name,
            description=input.description,
            status=input.status,
            priority=input.priority,
        )

    @strawberry.mutation
    async def update_blocker(self, id: int, input: BlockerUpdateInput) -> BlockerType | None:
        """Update mutation."""
        return BlockerType(
            id=id,
            name=input.name or 'updated',
            description=input.description or '',
            status=input.status or 'active',
            priority=input.priority or 'medium',
        )

    @strawberry.mutation
    async def delete_blocker(self, id: int) -> bool:
        """Delete mutation."""
        return True


@strawberry.type
class BlockerQueries:
    """Queries."""

    @strawberry.field
    async def blocker(self, id: int) -> BlockerType | None:
        """Get by ID."""
        return BlockerType(id=id, name='Test')

    @strawberry.field
    async def blockers(
        self,
        filter: BlockerFilterInput | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> BlockerConnection:
        """List query."""
        items = [BlockerType(id=i, name=f'Item {i}') for i in range(limit)]
        return BlockerConnection(items=items, total=limit)


def create_blocker_schema() -> strawberry.Schema:
    """Create schema."""
    return strawberry.Schema(query=BlockerQueries, mutation=BlockerMutations)

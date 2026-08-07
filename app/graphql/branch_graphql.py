"""GraphQL: branch - GraphQL schema and resolvers."""

from __future__ import annotations

from datetime import datetime

import strawberry


@strawberry.type
class BranchType:
    """GraphQL type."""
    id: int = 0
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'
    created_at: datetime = strawberry.field(default_factory=datetime.utcnow)
    updated_at: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type
class BranchConnection:
    """Connection type."""
    items: list[BranchType] = strawberry.field(default_factory=list)
    total: int = 0
    has_next_page: bool = False
    has_previous_page: bool = False


@strawberry.input
class BranchCreateInput:
    """Create input."""
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'


@strawberry.input
class BranchUpdateInput:
    """Update input."""
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.input
class BranchFilterInput:
    """Filter input."""
    search: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.type
class BranchMutations:
    """Mutations."""

    @strawberry.mutation
    async def create_branch(self, input: BranchCreateInput) -> BranchType:
        """Create mutation."""
        return BranchType(
            id=1,
            name=input.name,
            description=input.description,
            status=input.status,
            priority=input.priority,
        )

    @strawberry.mutation
    async def update_branch(self, id: int, input: BranchUpdateInput) -> BranchType | None:
        """Update mutation."""
        return BranchType(
            id=id,
            name=input.name or 'updated',
            description=input.description or '',
            status=input.status or 'active',
            priority=input.priority or 'medium',
        )

    @strawberry.mutation
    async def delete_branch(self, id: int) -> bool:
        """Delete mutation."""
        return True


@strawberry.type
class BranchQueries:
    """Queries."""

    @strawberry.field
    async def branch(self, id: int) -> BranchType | None:
        """Get by ID."""
        return BranchType(id=id, name='Test')

    @strawberry.field
    async def branchs(
        self,
        filter: BranchFilterInput | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> BranchConnection:
        """List query."""
        items = [BranchType(id=i, name=f'Item {i}') for i in range(limit)]
        return BranchConnection(items=items, total=limit)


def create_branch_schema() -> strawberry.Schema:
    """Create schema."""
    return strawberry.Schema(query=BranchQueries, mutation=BranchMutations)

"""GraphQL: comment - GraphQL schema and resolvers."""

from __future__ import annotations

from datetime import datetime

import strawberry


@strawberry.type
class CommentType:
    """GraphQL type."""
    id: int = 0
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'
    created_at: datetime = strawberry.field(default_factory=datetime.utcnow)
    updated_at: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type
class CommentConnection:
    """Connection type."""
    items: list[CommentType] = strawberry.field(default_factory=list)
    total: int = 0
    has_next_page: bool = False
    has_previous_page: bool = False


@strawberry.input
class CommentCreateInput:
    """Create input."""
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'


@strawberry.input
class CommentUpdateInput:
    """Update input."""
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.input
class CommentFilterInput:
    """Filter input."""
    search: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.type
class CommentMutations:
    """Mutations."""

    @strawberry.mutation
    async def create_comment(self, input: CommentCreateInput) -> CommentType:
        """Create mutation."""
        return CommentType(
            id=1,
            name=input.name,
            description=input.description,
            status=input.status,
            priority=input.priority,
        )

    @strawberry.mutation
    async def update_comment(self, id: int, input: CommentUpdateInput) -> CommentType | None:
        """Update mutation."""
        return CommentType(
            id=id,
            name=input.name or 'updated',
            description=input.description or '',
            status=input.status or 'active',
            priority=input.priority or 'medium',
        )

    @strawberry.mutation
    async def delete_comment(self, id: int) -> bool:
        """Delete mutation."""
        return True


@strawberry.type
class CommentQueries:
    """Queries."""

    @strawberry.field
    async def comment(self, id: int) -> CommentType | None:
        """Get by ID."""
        return CommentType(id=id, name='Test')

    @strawberry.field
    async def comments(
        self,
        filter: CommentFilterInput | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> CommentConnection:
        """List query."""
        items = [CommentType(id=i, name=f'Item {i}') for i in range(limit)]
        return CommentConnection(items=items, total=limit)


def create_comment_schema() -> strawberry.Schema:
    """Create schema."""
    return strawberry.Schema(query=CommentQueries, mutation=CommentMutations)

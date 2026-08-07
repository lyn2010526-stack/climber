"""GraphQL: user - GraphQL schema and resolvers."""

from __future__ import annotations

from datetime import datetime

import strawberry


@strawberry.type
class UserType:
    """GraphQL type."""
    id: int = 0
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'
    created_at: datetime = strawberry.field(default_factory=datetime.utcnow)
    updated_at: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type
class UserConnection:
    """Connection type."""
    items: list[UserType] = strawberry.field(default_factory=list)
    total: int = 0
    has_next_page: bool = False
    has_previous_page: bool = False


@strawberry.input
class UserCreateInput:
    """Create input."""
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'


@strawberry.input
class UserUpdateInput:
    """Update input."""
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.input
class UserFilterInput:
    """Filter input."""
    search: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.type
class UserMutations:
    """Mutations."""

    @strawberry.mutation
    async def create_user(self, input: UserCreateInput) -> UserType:
        """Create mutation."""
        return UserType(
            id=1,
            name=input.name,
            description=input.description,
            status=input.status,
            priority=input.priority,
        )

    @strawberry.mutation
    async def update_user(self, id: int, input: UserUpdateInput) -> UserType | None:
        """Update mutation."""
        return UserType(
            id=id,
            name=input.name or 'updated',
            description=input.description or '',
            status=input.status or 'active',
            priority=input.priority or 'medium',
        )

    @strawberry.mutation
    async def delete_user(self, id: int) -> bool:
        """Delete mutation."""
        return True


@strawberry.type
class UserQueries:
    """Queries."""

    @strawberry.field
    async def user(self, id: int) -> UserType | None:
        """Get by ID."""
        return UserType(id=id, name='Test')

    @strawberry.field
    async def users(
        self,
        filter: UserFilterInput | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> UserConnection:
        """List query."""
        items = [UserType(id=i, name=f'Item {i}') for i in range(limit)]
        return UserConnection(items=items, total=limit)


def create_user_schema() -> strawberry.Schema:
    """Create schema."""
    return strawberry.Schema(query=UserQueries, mutation=UserMutations)

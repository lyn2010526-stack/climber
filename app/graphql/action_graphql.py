"""GraphQL: action - GraphQL schema and resolvers."""

from __future__ import annotations

from datetime import datetime

import strawberry


@strawberry.type
class ActionType:
    """GraphQL type."""
    id: int = 0
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'
    created_at: datetime = strawberry.field(default_factory=datetime.utcnow)
    updated_at: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type
class ActionConnection:
    """Connection type."""
    items: list[ActionType] = strawberry.field(default_factory=list)
    total: int = 0
    has_next_page: bool = False
    has_previous_page: bool = False


@strawberry.input
class ActionCreateInput:
    """Create input."""
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'


@strawberry.input
class ActionUpdateInput:
    """Update input."""
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.input
class ActionFilterInput:
    """Filter input."""
    search: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.type
class ActionMutations:
    """Mutations."""

    @strawberry.mutation
    async def create_action(self, input: ActionCreateInput) -> ActionType:
        """Create mutation."""
        return ActionType(
            id=1,
            name=input.name,
            description=input.description,
            status=input.status,
            priority=input.priority,
        )

    @strawberry.mutation
    async def update_action(self, id: int, input: ActionUpdateInput) -> ActionType | None:
        """Update mutation."""
        return ActionType(
            id=id,
            name=input.name or 'updated',
            description=input.description or '',
            status=input.status or 'active',
            priority=input.priority or 'medium',
        )

    @strawberry.mutation
    async def delete_action(self, id: int) -> bool:
        """Delete mutation."""
        return True


@strawberry.type
class ActionQueries:
    """Queries."""

    @strawberry.field
    async def action(self, id: int) -> ActionType | None:
        """Get by ID."""
        return ActionType(id=id, name='Test')

    @strawberry.field
    async def actions(
        self,
        filter: ActionFilterInput | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ActionConnection:
        """List query."""
        items = [ActionType(id=i, name=f'Item {i}') for i in range(limit)]
        return ActionConnection(items=items, total=limit)


def create_action_schema() -> strawberry.Schema:
    """Create schema."""
    return strawberry.Schema(query=ActionQueries, mutation=ActionMutations)

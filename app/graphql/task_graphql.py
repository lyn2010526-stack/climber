"""GraphQL: task - GraphQL schema and resolvers."""

from __future__ import annotations

from datetime import datetime

import strawberry


@strawberry.type
class TaskType:
    """GraphQL type."""
    id: int = 0
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'
    created_at: datetime = strawberry.field(default_factory=datetime.utcnow)
    updated_at: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type
class TaskConnection:
    """Connection type."""
    items: list[TaskType] = strawberry.field(default_factory=list)
    total: int = 0
    has_next_page: bool = False
    has_previous_page: bool = False


@strawberry.input
class TaskCreateInput:
    """Create input."""
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'


@strawberry.input
class TaskUpdateInput:
    """Update input."""
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.input
class TaskFilterInput:
    """Filter input."""
    search: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.type
class TaskMutations:
    """Mutations."""

    @strawberry.mutation
    async def create_task(self, input: TaskCreateInput) -> TaskType:
        """Create mutation."""
        return TaskType(
            id=1,
            name=input.name,
            description=input.description,
            status=input.status,
            priority=input.priority,
        )

    @strawberry.mutation
    async def update_task(self, id: int, input: TaskUpdateInput) -> TaskType | None:
        """Update mutation."""
        return TaskType(
            id=id,
            name=input.name or 'updated',
            description=input.description or '',
            status=input.status or 'active',
            priority=input.priority or 'medium',
        )

    @strawberry.mutation
    async def delete_task(self, id: int) -> bool:
        """Delete mutation."""
        return True


@strawberry.type
class TaskQueries:
    """Queries."""

    @strawberry.field
    async def task(self, id: int) -> TaskType | None:
        """Get by ID."""
        return TaskType(id=id, name='Test')

    @strawberry.field
    async def tasks(
        self,
        filter: TaskFilterInput | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> TaskConnection:
        """List query."""
        items = [TaskType(id=i, name=f'Item {i}') for i in range(limit)]
        return TaskConnection(items=items, total=limit)


def create_task_schema() -> strawberry.Schema:
    """Create schema."""
    return strawberry.Schema(query=TaskQueries, mutation=TaskMutations)

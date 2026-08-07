"""GraphQL: project - GraphQL schema and resolvers."""

from __future__ import annotations

from datetime import datetime

import strawberry


@strawberry.type
class ProjectType:
    """GraphQL type."""
    id: int = 0
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'
    created_at: datetime = strawberry.field(default_factory=datetime.utcnow)
    updated_at: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type
class ProjectConnection:
    """Connection type."""
    items: list[ProjectType] = strawberry.field(default_factory=list)
    total: int = 0
    has_next_page: bool = False
    has_previous_page: bool = False


@strawberry.input
class ProjectCreateInput:
    """Create input."""
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'


@strawberry.input
class ProjectUpdateInput:
    """Update input."""
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.input
class ProjectFilterInput:
    """Filter input."""
    search: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.type
class ProjectMutations:
    """Mutations."""

    @strawberry.mutation
    async def create_project(self, input: ProjectCreateInput) -> ProjectType:
        """Create mutation."""
        return ProjectType(
            id=1,
            name=input.name,
            description=input.description,
            status=input.status,
            priority=input.priority,
        )

    @strawberry.mutation
    async def update_project(self, id: int, input: ProjectUpdateInput) -> ProjectType | None:
        """Update mutation."""
        return ProjectType(
            id=id,
            name=input.name or 'updated',
            description=input.description or '',
            status=input.status or 'active',
            priority=input.priority or 'medium',
        )

    @strawberry.mutation
    async def delete_project(self, id: int) -> bool:
        """Delete mutation."""
        return True


@strawberry.type
class ProjectQueries:
    """Queries."""

    @strawberry.field
    async def project(self, id: int) -> ProjectType | None:
        """Get by ID."""
        return ProjectType(id=id, name='Test')

    @strawberry.field
    async def projects(
        self,
        filter: ProjectFilterInput | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ProjectConnection:
        """List query."""
        items = [ProjectType(id=i, name=f'Item {i}') for i in range(limit)]
        return ProjectConnection(items=items, total=limit)


def create_project_schema() -> strawberry.Schema:
    """Create schema."""
    return strawberry.Schema(query=ProjectQueries, mutation=ProjectMutations)

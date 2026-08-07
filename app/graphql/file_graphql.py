"""GraphQL: file - GraphQL schema and resolvers."""

from __future__ import annotations

from datetime import datetime

import strawberry


@strawberry.type
class FileType:
    """GraphQL type."""
    id: int = 0
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'
    created_at: datetime = strawberry.field(default_factory=datetime.utcnow)
    updated_at: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type
class FileConnection:
    """Connection type."""
    items: list[FileType] = strawberry.field(default_factory=list)
    total: int = 0
    has_next_page: bool = False
    has_previous_page: bool = False


@strawberry.input
class FileCreateInput:
    """Create input."""
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'


@strawberry.input
class FileUpdateInput:
    """Update input."""
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.input
class FileFilterInput:
    """Filter input."""
    search: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.type
class FileMutations:
    """Mutations."""

    @strawberry.mutation
    async def create_file(self, input: FileCreateInput) -> FileType:
        """Create mutation."""
        return FileType(
            id=1,
            name=input.name,
            description=input.description,
            status=input.status,
            priority=input.priority,
        )

    @strawberry.mutation
    async def update_file(self, id: int, input: FileUpdateInput) -> FileType | None:
        """Update mutation."""
        return FileType(
            id=id,
            name=input.name or 'updated',
            description=input.description or '',
            status=input.status or 'active',
            priority=input.priority or 'medium',
        )

    @strawberry.mutation
    async def delete_file(self, id: int) -> bool:
        """Delete mutation."""
        return True


@strawberry.type
class FileQueries:
    """Queries."""

    @strawberry.field
    async def file(self, id: int) -> FileType | None:
        """Get by ID."""
        return FileType(id=id, name='Test')

    @strawberry.field
    async def files(
        self,
        filter: FileFilterInput | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> FileConnection:
        """List query."""
        items = [FileType(id=i, name=f'Item {i}') for i in range(limit)]
        return FileConnection(items=items, total=limit)


def create_file_schema() -> strawberry.Schema:
    """Create schema."""
    return strawberry.Schema(query=FileQueries, mutation=FileMutations)

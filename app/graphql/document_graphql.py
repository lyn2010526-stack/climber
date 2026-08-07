"""GraphQL: document - GraphQL schema and resolvers."""

from __future__ import annotations

from datetime import datetime

import strawberry


@strawberry.type
class DocumentType:
    """GraphQL type."""
    id: int = 0
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'
    created_at: datetime = strawberry.field(default_factory=datetime.utcnow)
    updated_at: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type
class DocumentConnection:
    """Connection type."""
    items: list[DocumentType] = strawberry.field(default_factory=list)
    total: int = 0
    has_next_page: bool = False
    has_previous_page: bool = False


@strawberry.input
class DocumentCreateInput:
    """Create input."""
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'


@strawberry.input
class DocumentUpdateInput:
    """Update input."""
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.input
class DocumentFilterInput:
    """Filter input."""
    search: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.type
class DocumentMutations:
    """Mutations."""

    @strawberry.mutation
    async def create_document(self, input: DocumentCreateInput) -> DocumentType:
        """Create mutation."""
        return DocumentType(
            id=1,
            name=input.name,
            description=input.description,
            status=input.status,
            priority=input.priority,
        )

    @strawberry.mutation
    async def update_document(self, id: int, input: DocumentUpdateInput) -> DocumentType | None:
        """Update mutation."""
        return DocumentType(
            id=id,
            name=input.name or 'updated',
            description=input.description or '',
            status=input.status or 'active',
            priority=input.priority or 'medium',
        )

    @strawberry.mutation
    async def delete_document(self, id: int) -> bool:
        """Delete mutation."""
        return True


@strawberry.type
class DocumentQueries:
    """Queries."""

    @strawberry.field
    async def document(self, id: int) -> DocumentType | None:
        """Get by ID."""
        return DocumentType(id=id, name='Test')

    @strawberry.field
    async def documents(
        self,
        filter: DocumentFilterInput | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> DocumentConnection:
        """List query."""
        items = [DocumentType(id=i, name=f'Item {i}') for i in range(limit)]
        return DocumentConnection(items=items, total=limit)


def create_document_schema() -> strawberry.Schema:
    """Create schema."""
    return strawberry.Schema(query=DocumentQueries, mutation=DocumentMutations)

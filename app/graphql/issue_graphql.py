"""GraphQL: issue - GraphQL schema and resolvers."""

from __future__ import annotations

from datetime import datetime

import strawberry


@strawberry.type
class IssueType:
    """GraphQL type."""
    id: int = 0
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'
    created_at: datetime = strawberry.field(default_factory=datetime.utcnow)
    updated_at: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type
class IssueConnection:
    """Connection type."""
    items: list[IssueType] = strawberry.field(default_factory=list)
    total: int = 0
    has_next_page: bool = False
    has_previous_page: bool = False


@strawberry.input
class IssueCreateInput:
    """Create input."""
    name: str = ''
    description: str = ''
    status: str = 'active'
    priority: str = 'medium'


@strawberry.input
class IssueUpdateInput:
    """Update input."""
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.input
class IssueFilterInput:
    """Filter input."""
    search: str | None = None
    status: str | None = None
    priority: str | None = None


@strawberry.type
class IssueMutations:
    """Mutations."""

    @strawberry.mutation
    async def create_issue(self, input: IssueCreateInput) -> IssueType:
        """Create mutation."""
        return IssueType(
            id=1,
            name=input.name,
            description=input.description,
            status=input.status,
            priority=input.priority,
        )

    @strawberry.mutation
    async def update_issue(self, id: int, input: IssueUpdateInput) -> IssueType | None:
        """Update mutation."""
        return IssueType(
            id=id,
            name=input.name or 'updated',
            description=input.description or '',
            status=input.status or 'active',
            priority=input.priority or 'medium',
        )

    @strawberry.mutation
    async def delete_issue(self, id: int) -> bool:
        """Delete mutation."""
        return True


@strawberry.type
class IssueQueries:
    """Queries."""

    @strawberry.field
    async def issue(self, id: int) -> IssueType | None:
        """Get by ID."""
        return IssueType(id=id, name='Test')

    @strawberry.field
    async def issues(
        self,
        filter: IssueFilterInput | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> IssueConnection:
        """List query."""
        items = [IssueType(id=i, name=f'Item {i}') for i in range(limit)]
        return IssueConnection(items=items, total=limit)


def create_issue_schema() -> strawberry.Schema:
    """Create schema."""
    return strawberry.Schema(query=IssueQueries, mutation=IssueMutations)

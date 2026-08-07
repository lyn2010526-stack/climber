"""Tests for branch GraphQL."""

import pytest

from app.graphql.branch_graphql import (
    BranchCreateInput,
    BranchMutations,
    BranchQueries,
    create_branch_schema,
)


class TestBranchGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = BranchCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_branch_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = BranchQueries()
        result = await queries.branch(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = BranchMutations()
        input_data = BranchCreateInput(name='Test')
        result = await mutations.create_branch(input=input_data)
        assert result.name == 'Test'

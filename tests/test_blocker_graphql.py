"""Tests for blocker GraphQL."""

import pytest

from app.graphql.blocker_graphql import (
    BlockerCreateInput,
    BlockerMutations,
    BlockerQueries,
    create_blocker_schema,
)


class TestBlockerGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = BlockerCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_blocker_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = BlockerQueries()
        result = await queries.blocker(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = BlockerMutations()
        input_data = BlockerCreateInput(name='Test')
        result = await mutations.create_blocker(input=input_data)
        assert result.name == 'Test'

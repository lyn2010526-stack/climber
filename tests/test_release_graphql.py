"""Tests for release GraphQL."""

import pytest

from app.graphql.release_graphql import (
    ReleaseCreateInput,
    ReleaseMutations,
    ReleaseQueries,
    create_release_schema,
)


class TestReleaseGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = ReleaseCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_release_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = ReleaseQueries()
        result = await queries.release(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = ReleaseMutations()
        input_data = ReleaseCreateInput(name='Test')
        result = await mutations.create_release(input=input_data)
        assert result.name == 'Test'

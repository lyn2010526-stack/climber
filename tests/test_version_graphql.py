"""Tests for version GraphQL."""

import pytest

from app.graphql.version_graphql import (
    VersionCreateInput,
    VersionMutations,
    VersionQueries,
    create_version_schema,
)


class TestVersionGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = VersionCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_version_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = VersionQueries()
        result = await queries.version(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = VersionMutations()
        input_data = VersionCreateInput(name='Test')
        result = await mutations.create_version(input=input_data)
        assert result.name == 'Test'

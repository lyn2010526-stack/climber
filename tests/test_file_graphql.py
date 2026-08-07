"""Tests for file GraphQL."""

import pytest

from app.graphql.file_graphql import (
    FileCreateInput,
    FileMutations,
    FileQueries,
    create_file_schema,
)


class TestFileGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = FileCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_file_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = FileQueries()
        result = await queries.file(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = FileMutations()
        input_data = FileCreateInput(name='Test')
        result = await mutations.create_file(input=input_data)
        assert result.name == 'Test'

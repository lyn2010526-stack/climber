"""Tests for dependency GraphQL."""

import pytest

from app.graphql.dependency_graphql import (
    DependencyCreateInput,
    DependencyMutations,
    DependencyQueries,
    create_dependency_schema,
)


class TestDependencyGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = DependencyCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_dependency_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = DependencyQueries()
        result = await queries.dependency(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = DependencyMutations()
        input_data = DependencyCreateInput(name='Test')
        result = await mutations.create_dependency(input=input_data)
        assert result.name == 'Test'

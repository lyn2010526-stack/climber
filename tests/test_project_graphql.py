"""Tests for project GraphQL."""

import pytest

from app.graphql.project_graphql import (
    ProjectCreateInput,
    ProjectMutations,
    ProjectQueries,
    create_project_schema,
)


class TestProjectGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = ProjectCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_project_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = ProjectQueries()
        result = await queries.project(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = ProjectMutations()
        input_data = ProjectCreateInput(name='Test')
        result = await mutations.create_project(input=input_data)
        assert result.name == 'Test'

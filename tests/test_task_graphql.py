"""Tests for task GraphQL."""

import pytest

from app.graphql.task_graphql import (
    TaskCreateInput,
    TaskMutations,
    TaskQueries,
    create_task_schema,
)


class TestTaskGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = TaskCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_task_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = TaskQueries()
        result = await queries.task(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = TaskMutations()
        input_data = TaskCreateInput(name='Test')
        result = await mutations.create_task(input=input_data)
        assert result.name == 'Test'

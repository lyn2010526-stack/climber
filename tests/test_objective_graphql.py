"""Tests for objective GraphQL."""

import pytest

from app.graphql.objective_graphql import (
    ObjectiveCreateInput,
    ObjectiveMutations,
    ObjectiveQueries,
    create_objective_schema,
)


class TestObjectiveGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = ObjectiveCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_objective_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = ObjectiveQueries()
        result = await queries.objective(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = ObjectiveMutations()
        input_data = ObjectiveCreateInput(name='Test')
        result = await mutations.create_objective(input=input_data)
        assert result.name == 'Test'

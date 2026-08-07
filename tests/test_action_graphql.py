"""Tests for action GraphQL."""

import pytest

from app.graphql.action_graphql import (
    ActionCreateInput,
    ActionMutations,
    ActionQueries,
    create_action_schema,
)


class TestActionGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = ActionCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_action_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = ActionQueries()
        result = await queries.action(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = ActionMutations()
        input_data = ActionCreateInput(name='Test')
        result = await mutations.create_action(input=input_data)
        assert result.name == 'Test'

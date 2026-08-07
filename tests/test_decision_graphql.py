"""Tests for decision GraphQL."""

import pytest

from app.graphql.decision_graphql import (
    DecisionCreateInput,
    DecisionMutations,
    DecisionQueries,
    create_decision_schema,
)


class TestDecisionGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = DecisionCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_decision_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = DecisionQueries()
        result = await queries.decision(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = DecisionMutations()
        input_data = DecisionCreateInput(name='Test')
        result = await mutations.create_decision(input=input_data)
        assert result.name == 'Test'

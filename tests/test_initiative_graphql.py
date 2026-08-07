"""Tests for initiative GraphQL."""

import pytest

from app.graphql.initiative_graphql import (
    InitiativeCreateInput,
    InitiativeMutations,
    InitiativeQueries,
    create_initiative_schema,
)


class TestInitiativeGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = InitiativeCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_initiative_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = InitiativeQueries()
        result = await queries.initiative(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = InitiativeMutations()
        input_data = InitiativeCreateInput(name='Test')
        result = await mutations.create_initiative(input=input_data)
        assert result.name == 'Test'

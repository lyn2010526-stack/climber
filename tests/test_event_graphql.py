"""Tests for event GraphQL."""

import pytest

from app.graphql.event_graphql import (
    EventCreateInput,
    EventMutations,
    EventQueries,
    create_event_schema,
)


class TestEventGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = EventCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_event_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = EventQueries()
        result = await queries.event(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = EventMutations()
        input_data = EventCreateInput(name='Test')
        result = await mutations.create_event(input=input_data)
        assert result.name == 'Test'

"""Tests for message GraphQL."""

import pytest

from app.graphql.message_graphql import (
    MessageCreateInput,
    MessageMutations,
    MessageQueries,
    create_message_schema,
)


class TestMessageGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = MessageCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_message_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = MessageQueries()
        result = await queries.message(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = MessageMutations()
        input_data = MessageCreateInput(name='Test')
        result = await mutations.create_message(input=input_data)
        assert result.name == 'Test'

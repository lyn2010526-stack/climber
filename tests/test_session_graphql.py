"""Tests for session GraphQL."""

import pytest

from app.graphql.session_graphql import (
    SessionCreateInput,
    SessionMutations,
    SessionQueries,
    create_session_schema,
)


class TestSessionGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = SessionCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_session_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = SessionQueries()
        result = await queries.session(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = SessionMutations()
        input_data = SessionCreateInput(name='Test')
        result = await mutations.create_session(input=input_data)
        assert result.name == 'Test'

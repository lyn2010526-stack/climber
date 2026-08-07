"""Tests for user GraphQL."""

import pytest

from app.graphql.user_graphql import (
    UserCreateInput,
    UserMutations,
    UserQueries,
    create_user_schema,
)


class TestUserGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = UserCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_user_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = UserQueries()
        result = await queries.user(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = UserMutations()
        input_data = UserCreateInput(name='Test')
        result = await mutations.create_user(input=input_data)
        assert result.name == 'Test'

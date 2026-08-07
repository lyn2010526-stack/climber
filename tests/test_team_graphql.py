"""Tests for team GraphQL."""

import pytest

from app.graphql.team_graphql import (
    TeamCreateInput,
    TeamMutations,
    TeamQueries,
    create_team_schema,
)


class TestTeamGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = TeamCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_team_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = TeamQueries()
        result = await queries.team(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = TeamMutations()
        input_data = TeamCreateInput(name='Test')
        result = await mutations.create_team(input=input_data)
        assert result.name == 'Test'

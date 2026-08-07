"""Tests for goal GraphQL."""

import pytest

from app.graphql.goal_graphql import (
    GoalCreateInput,
    GoalMutations,
    GoalQueries,
    create_goal_schema,
)


class TestGoalGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = GoalCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_goal_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = GoalQueries()
        result = await queries.goal(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = GoalMutations()
        input_data = GoalCreateInput(name='Test')
        result = await mutations.create_goal(input=input_data)
        assert result.name == 'Test'

"""Tests for dashboard GraphQL."""

import pytest

from app.graphql.dashboard_graphql import (
    DashboardCreateInput,
    DashboardMutations,
    DashboardQueries,
    create_dashboard_schema,
)


class TestDashboardGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = DashboardCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_dashboard_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = DashboardQueries()
        result = await queries.dashboard(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = DashboardMutations()
        input_data = DashboardCreateInput(name='Test')
        result = await mutations.create_dashboard(input=input_data)
        assert result.name == 'Test'

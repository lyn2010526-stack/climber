"""Tests for chart GraphQL."""

import pytest

from app.graphql.chart_graphql import (
    ChartCreateInput,
    ChartMutations,
    ChartQueries,
    create_chart_schema,
)


class TestChartGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = ChartCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_chart_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = ChartQueries()
        result = await queries.chart(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = ChartMutations()
        input_data = ChartCreateInput(name='Test')
        result = await mutations.create_chart(input=input_data)
        assert result.name == 'Test'

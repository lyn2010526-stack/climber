"""Tests for analytics GraphQL."""

import pytest

from app.graphql.analytics_graphql import (
    AnalyticsCreateInput,
    AnalyticsMutations,
    AnalyticsQueries,
    create_analytics_schema,
)


class TestAnalyticsGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = AnalyticsCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_analytics_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = AnalyticsQueries()
        result = await queries.analytics(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = AnalyticsMutations()
        input_data = AnalyticsCreateInput(name='Test')
        result = await mutations.create_analytics(input=input_data)
        assert result.name == 'Test'

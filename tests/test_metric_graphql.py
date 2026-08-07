"""Tests for metric GraphQL."""

import pytest

from app.graphql.metric_graphql import (
    MetricCreateInput,
    MetricMutations,
    MetricQueries,
    create_metric_schema,
)


class TestMetricGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = MetricCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_metric_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = MetricQueries()
        result = await queries.metric(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = MetricMutations()
        input_data = MetricCreateInput(name='Test')
        result = await mutations.create_metric(input=input_data)
        assert result.name == 'Test'

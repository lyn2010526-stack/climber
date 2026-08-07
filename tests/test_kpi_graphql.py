"""Tests for kpi GraphQL."""

import pytest

from app.graphql.kpi_graphql import (
    KpiCreateInput,
    KpiMutations,
    KpiQueries,
    create_kpi_schema,
)


class TestKpiGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = KpiCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_kpi_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = KpiQueries()
        result = await queries.kpi(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = KpiMutations()
        input_data = KpiCreateInput(name='Test')
        result = await mutations.create_kpi(input=input_data)
        assert result.name == 'Test'

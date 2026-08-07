"""Tests for risk GraphQL."""

import pytest

from app.graphql.risk_graphql import (
    RiskCreateInput,
    RiskMutations,
    RiskQueries,
    create_risk_schema,
)


class TestRiskGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = RiskCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_risk_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = RiskQueries()
        result = await queries.risk(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = RiskMutations()
        input_data = RiskCreateInput(name='Test')
        result = await mutations.create_risk(input=input_data)
        assert result.name == 'Test'

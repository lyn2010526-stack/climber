"""Tests for report GraphQL."""

import pytest

from app.graphql.report_graphql import (
    ReportCreateInput,
    ReportMutations,
    ReportQueries,
    create_report_schema,
)


class TestReportGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = ReportCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_report_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = ReportQueries()
        result = await queries.report(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = ReportMutations()
        input_data = ReportCreateInput(name='Test')
        result = await mutations.create_report(input=input_data)
        assert result.name == 'Test'

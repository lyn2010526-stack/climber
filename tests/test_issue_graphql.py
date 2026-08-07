"""Tests for issue GraphQL."""

import pytest

from app.graphql.issue_graphql import (
    IssueCreateInput,
    IssueMutations,
    IssueQueries,
    create_issue_schema,
)


class TestIssueGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = IssueCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_issue_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = IssueQueries()
        result = await queries.issue(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = IssueMutations()
        input_data = IssueCreateInput(name='Test')
        result = await mutations.create_issue(input=input_data)
        assert result.name == 'Test'

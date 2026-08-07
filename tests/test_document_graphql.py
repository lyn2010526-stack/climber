"""Tests for document GraphQL."""

import pytest

from app.graphql.document_graphql import (
    DocumentCreateInput,
    DocumentMutations,
    DocumentQueries,
    create_document_schema,
)


class TestDocumentGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = DocumentCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_document_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = DocumentQueries()
        result = await queries.document(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = DocumentMutations()
        input_data = DocumentCreateInput(name='Test')
        result = await mutations.create_document(input=input_data)
        assert result.name == 'Test'

"""Tests for comment GraphQL."""

import pytest

from app.graphql.comment_graphql import (
    CommentCreateInput,
    CommentMutations,
    CommentQueries,
    create_comment_schema,
)


class TestCommentGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = CommentCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_comment_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = CommentQueries()
        result = await queries.comment(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = CommentMutations()
        input_data = CommentCreateInput(name='Test')
        result = await mutations.create_comment(input=input_data)
        assert result.name == 'Test'

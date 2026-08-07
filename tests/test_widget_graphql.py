"""Tests for widget GraphQL."""

import pytest

from app.graphql.widget_graphql import (
    WidgetCreateInput,
    WidgetMutations,
    WidgetQueries,
    create_widget_schema,
)


class TestWidgetGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = WidgetCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_widget_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = WidgetQueries()
        result = await queries.widget(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = WidgetMutations()
        input_data = WidgetCreateInput(name='Test')
        result = await mutations.create_widget(input=input_data)
        assert result.name == 'Test'

"""Tests for notification GraphQL."""

import pytest

from app.graphql.notification_graphql import (
    NotificationCreateInput,
    NotificationMutations,
    NotificationQueries,
    create_notification_schema,
)


class TestNotificationGraphQL:
    """Tests for GraphQL."""

    def test_create_input(self):
        input_data = NotificationCreateInput(name='Test')
        assert input_data.name == 'Test'

    def test_schema_creation(self):
        schema = create_notification_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_query(self):
        queries = NotificationQueries()
        result = await queries.notification(id=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_mutation(self):
        mutations = NotificationMutations()
        input_data = NotificationCreateInput(name='Test')
        result = await mutations.create_notification(input=input_data)
        assert result.name == 'Test'

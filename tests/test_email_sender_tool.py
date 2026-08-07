"""Tests for email_sender tool."""

import pytest

from app.tools.email_sender_tool import (
    EmailSenderTool,
    EmailSenderToolInput,
)


class TestEmailSenderTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = EmailSenderTool()
        inp = EmailSenderToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = EmailSenderTool()
        assert tool.name == 'email_sender'
        assert tool.description

"""Tests for audio_transcriber tool."""

import pytest

from app.tools.audio_transcriber_tool import (
    AudioTranscriberTool,
    AudioTranscriberToolInput,
    AudioTranscriberToolRegistry,
)


class TestAudioTranscriberTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = AudioTranscriberTool()
        input_data = AudioTranscriberToolInput(query='test')
        result = await tool.execute(input_data)
        assert result.success

    def test_registry(self):
        registry = AudioTranscriberToolRegistry()
        tool = AudioTranscriberTool()
        registry.register(tool)
        assert registry.get(tool.name) is not None

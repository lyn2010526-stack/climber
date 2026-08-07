"""Tests for stream processor."""

import pytest

from app.processors.stream_processor import (
    StreamProcessor,
    StreamProcessorConfig,
    StreamProcessorPipeline,
)


class TestStreamProcessor:
    """Tests for processor."""

    @pytest.mark.asyncio
    async def test_process(self):
        processor = StreamProcessor()
        result = await processor.process({'key': 'value'})
        assert result.success is True
        assert result.data == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_process_batch(self):
        processor = StreamProcessor(config=StreamProcessorConfig(batch_size=2))
        items = [{'id': i} for i in range(5)]
        results = await processor.process_batch(items)
        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_pipeline(self):
        pipeline = StreamProcessorPipeline()
        pipeline.add_processor(StreamProcessor())
        pipeline.add_processor(StreamProcessor())
        result = await pipeline.execute({'data': 'test'})
        assert result.success is True

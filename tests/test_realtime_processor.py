"""Tests for realtime processor."""

import pytest

from app.processors.realtime_processor import (
    RealtimeProcessor,
    RealtimeProcessorConfig,
    RealtimeProcessorPipeline,
)


class TestRealtimeProcessor:
    """Tests for processor."""

    @pytest.mark.asyncio
    async def test_process(self):
        processor = RealtimeProcessor()
        result = await processor.process({'key': 'value'})
        assert result.success is True
        assert result.data == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_process_batch(self):
        processor = RealtimeProcessor(config=RealtimeProcessorConfig(batch_size=2))
        items = [{'id': i} for i in range(5)]
        results = await processor.process_batch(items)
        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_pipeline(self):
        pipeline = RealtimeProcessorPipeline()
        pipeline.add_processor(RealtimeProcessor())
        pipeline.add_processor(RealtimeProcessor())
        result = await pipeline.execute({'data': 'test'})
        assert result.success is True

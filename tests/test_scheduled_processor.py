"""Tests for scheduled processor."""

import pytest

from app.processors.scheduled_processor import (
    ScheduledProcessor,
    ScheduledProcessorConfig,
    ScheduledProcessorPipeline,
)


class TestScheduledProcessor:
    """Tests for processor."""

    @pytest.mark.asyncio
    async def test_process(self):
        processor = ScheduledProcessor()
        result = await processor.process({'key': 'value'})
        assert result.success is True
        assert result.data == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_process_batch(self):
        processor = ScheduledProcessor(config=ScheduledProcessorConfig(batch_size=2))
        items = [{'id': i} for i in range(5)]
        results = await processor.process_batch(items)
        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_pipeline(self):
        pipeline = ScheduledProcessorPipeline()
        pipeline.add_processor(ScheduledProcessor())
        pipeline.add_processor(ScheduledProcessor())
        result = await pipeline.execute({'data': 'test'})
        assert result.success is True

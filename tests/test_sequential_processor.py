"""Tests for sequential processor."""

import pytest

from app.processors.sequential_processor import (
    SequentialProcessor,
    SequentialProcessorConfig,
    SequentialProcessorPipeline,
)


class TestSequentialProcessor:
    """Tests for processor."""

    @pytest.mark.asyncio
    async def test_process(self):
        processor = SequentialProcessor()
        result = await processor.process({'key': 'value'})
        assert result.success is True
        assert result.data == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_process_batch(self):
        processor = SequentialProcessor(config=SequentialProcessorConfig(batch_size=2))
        items = [{'id': i} for i in range(5)]
        results = await processor.process_batch(items)
        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_pipeline(self):
        pipeline = SequentialProcessorPipeline()
        pipeline.add_processor(SequentialProcessor())
        pipeline.add_processor(SequentialProcessor())
        result = await pipeline.execute({'data': 'test'})
        assert result.success is True

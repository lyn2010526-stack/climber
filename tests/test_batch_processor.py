"""Tests for batch processor."""

import pytest

from app.processors.batch_processor import (
    BatchProcessor,
    BatchProcessorConfig,
    BatchProcessorPipeline,
)


class TestBatchProcessor:
    """Tests for processor."""

    @pytest.mark.asyncio
    async def test_process(self):
        processor = BatchProcessor()
        result = await processor.process({'key': 'value'})
        assert result.success is True
        assert result.data == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_process_batch(self):
        processor = BatchProcessor(config=BatchProcessorConfig(batch_size=2))
        items = [{'id': i} for i in range(5)]
        results = await processor.process_batch(items)
        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_pipeline(self):
        pipeline = BatchProcessorPipeline()
        pipeline.add_processor(BatchProcessor())
        pipeline.add_processor(BatchProcessor())
        result = await pipeline.execute({'data': 'test'})
        assert result.success is True

"""Tests for full processor."""

import pytest

from app.processors.full_processor import (
    FullProcessor,
    FullProcessorConfig,
    FullProcessorPipeline,
)


class TestFullProcessor:
    """Tests for processor."""

    @pytest.mark.asyncio
    async def test_process(self):
        processor = FullProcessor()
        result = await processor.process({'key': 'value'})
        assert result.success is True
        assert result.data == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_process_batch(self):
        processor = FullProcessor(config=FullProcessorConfig(batch_size=2))
        items = [{'id': i} for i in range(5)]
        results = await processor.process_batch(items)
        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_pipeline(self):
        pipeline = FullProcessorPipeline()
        pipeline.add_processor(FullProcessor())
        pipeline.add_processor(FullProcessor())
        result = await pipeline.execute({'data': 'test'})
        assert result.success is True

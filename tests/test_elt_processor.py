"""Tests for elt processor."""

import pytest

from app.processors.elt_processor import (
    EltProcessor,
    EltProcessorConfig,
    EltProcessorPipeline,
)


class TestEltProcessor:
    """Tests for processor."""

    @pytest.mark.asyncio
    async def test_process(self):
        processor = EltProcessor()
        result = await processor.process({'key': 'value'})
        assert result.success is True
        assert result.data == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_process_batch(self):
        processor = EltProcessor(config=EltProcessorConfig(batch_size=2))
        items = [{'id': i} for i in range(5)]
        results = await processor.process_batch(items)
        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_pipeline(self):
        pipeline = EltProcessorPipeline()
        pipeline.add_processor(EltProcessor())
        pipeline.add_processor(EltProcessor())
        result = await pipeline.execute({'data': 'test'})
        assert result.success is True

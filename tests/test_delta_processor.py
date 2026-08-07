"""Tests for delta processor."""

import pytest

from app.processors.delta_processor import (
    DeltaProcessor,
    DeltaProcessorConfig,
    DeltaProcessorPipeline,
)


class TestDeltaProcessor:
    """Tests for processor."""

    @pytest.mark.asyncio
    async def test_process(self):
        processor = DeltaProcessor()
        result = await processor.process({'key': 'value'})
        assert result.success is True
        assert result.data == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_process_batch(self):
        processor = DeltaProcessor(config=DeltaProcessorConfig(batch_size=2))
        items = [{'id': i} for i in range(5)]
        results = await processor.process_batch(items)
        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_pipeline(self):
        pipeline = DeltaProcessorPipeline()
        pipeline.add_processor(DeltaProcessor())
        pipeline.add_processor(DeltaProcessor())
        result = await pipeline.execute({'data': 'test'})
        assert result.success is True

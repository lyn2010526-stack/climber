"""Tests for incremental processor."""

import pytest

from app.processors.incremental_processor import (
    IncrementalProcessor,
    IncrementalProcessorConfig,
    IncrementalProcessorPipeline,
)


class TestIncrementalProcessor:
    """Tests for processor."""

    @pytest.mark.asyncio
    async def test_process(self):
        processor = IncrementalProcessor()
        result = await processor.process({'key': 'value'})
        assert result.success is True
        assert result.data == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_process_batch(self):
        processor = IncrementalProcessor(config=IncrementalProcessorConfig(batch_size=2))
        items = [{'id': i} for i in range(5)]
        results = await processor.process_batch(items)
        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_pipeline(self):
        pipeline = IncrementalProcessorPipeline()
        pipeline.add_processor(IncrementalProcessor())
        pipeline.add_processor(IncrementalProcessor())
        result = await pipeline.execute({'data': 'test'})
        assert result.success is True

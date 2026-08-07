"""Tests for data_profiling processor."""

import pytest

from app.processors.data_profiling_processor import (
    DataProfilingProcessor,
    DataProfilingProcessorConfig,
    DataProfilingProcessorPipeline,
)


class TestDataProfilingProcessor:
    """Tests for processor."""

    @pytest.mark.asyncio
    async def test_process(self):
        processor = DataProfilingProcessor()
        result = await processor.process({'key': 'value'})
        assert result.success is True
        assert result.data == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_process_batch(self):
        processor = DataProfilingProcessor(config=DataProfilingProcessorConfig(batch_size=2))
        items = [{'id': i} for i in range(5)]
        results = await processor.process_batch(items)
        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_pipeline(self):
        pipeline = DataProfilingProcessorPipeline()
        pipeline.add_processor(DataProfilingProcessor())
        pipeline.add_processor(DataProfilingProcessor())
        result = await pipeline.execute({'data': 'test'})
        assert result.success is True

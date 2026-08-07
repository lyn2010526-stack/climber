"""Tests for data_matching processor."""

import pytest

from app.processors.data_matching_processor import (
    DataMatchingProcessor,
    DataMatchingProcessorConfig,
    DataMatchingProcessorPipeline,
)


class TestDataMatchingProcessor:
    """Tests for processor."""

    @pytest.mark.asyncio
    async def test_process(self):
        processor = DataMatchingProcessor()
        result = await processor.process({'key': 'value'})
        assert result.success is True
        assert result.data == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_process_batch(self):
        processor = DataMatchingProcessor(config=DataMatchingProcessorConfig(batch_size=2))
        items = [{'id': i} for i in range(5)]
        results = await processor.process_batch(items)
        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_pipeline(self):
        pipeline = DataMatchingProcessorPipeline()
        pipeline.add_processor(DataMatchingProcessor())
        pipeline.add_processor(DataMatchingProcessor())
        result = await pipeline.execute({'data': 'test'})
        assert result.success is True

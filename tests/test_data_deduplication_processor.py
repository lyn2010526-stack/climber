"""Tests for data_deduplication processor."""

import pytest

from app.processors.data_deduplication_processor import (
    DataDeduplicationProcessor,
    DataDeduplicationProcessorConfig,
    DataDeduplicationProcessorPipeline,
)


class TestDataDeduplicationProcessor:
    """Tests for processor."""

    @pytest.mark.asyncio
    async def test_process(self):
        processor = DataDeduplicationProcessor()
        result = await processor.process({'key': 'value'})
        assert result.success is True
        assert result.data == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_process_batch(self):
        processor = DataDeduplicationProcessor(config=DataDeduplicationProcessorConfig(batch_size=2))
        items = [{'id': i} for i in range(5)]
        results = await processor.process_batch(items)
        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_pipeline(self):
        pipeline = DataDeduplicationProcessorPipeline()
        pipeline.add_processor(DataDeduplicationProcessor())
        pipeline.add_processor(DataDeduplicationProcessor())
        result = await pipeline.execute({'data': 'test'})
        assert result.success is True

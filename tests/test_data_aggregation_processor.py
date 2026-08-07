"""Tests for data_aggregation processor."""

import pytest

from app.processors.data_aggregation_processor import (
    DataAggregationProcessor,
    DataAggregationProcessorConfig,
    DataAggregationProcessorPipeline,
)


class TestDataAggregationProcessor:
    """Tests for processor."""

    @pytest.mark.asyncio
    async def test_process(self):
        processor = DataAggregationProcessor()
        result = await processor.process({'key': 'value'})
        assert result.success is True
        assert result.data == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_process_batch(self):
        processor = DataAggregationProcessor(config=DataAggregationProcessorConfig(batch_size=2))
        items = [{'id': i} for i in range(5)]
        results = await processor.process_batch(items)
        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_pipeline(self):
        pipeline = DataAggregationProcessorPipeline()
        pipeline.add_processor(DataAggregationProcessor())
        pipeline.add_processor(DataAggregationProcessor())
        result = await pipeline.execute({'data': 'test'})
        assert result.success is True

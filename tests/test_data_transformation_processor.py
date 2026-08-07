"""Tests for data_transformation processor."""

import pytest

from app.processors.data_transformation_processor import (
    DataTransformationProcessor,
    DataTransformationProcessorConfig,
    DataTransformationProcessorPipeline,
)


class TestDataTransformationProcessor:
    """Tests for processor."""

    @pytest.mark.asyncio
    async def test_process(self):
        processor = DataTransformationProcessor()
        result = await processor.process({'key': 'value'})
        assert result.success is True
        assert result.data == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_process_batch(self):
        processor = DataTransformationProcessor(config=DataTransformationProcessorConfig(batch_size=2))
        items = [{'id': i} for i in range(5)]
        results = await processor.process_batch(items)
        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_pipeline(self):
        pipeline = DataTransformationProcessorPipeline()
        pipeline.add_processor(DataTransformationProcessor())
        pipeline.add_processor(DataTransformationProcessor())
        result = await pipeline.execute({'data': 'test'})
        assert result.success is True

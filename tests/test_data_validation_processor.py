"""Tests for data_validation processor."""

import pytest

from app.processors.data_validation_processor import (
    DataValidationProcessor,
    DataValidationProcessorConfig,
    DataValidationProcessorPipeline,
)


class TestDataValidationProcessor:
    """Tests for processor."""

    @pytest.mark.asyncio
    async def test_process(self):
        processor = DataValidationProcessor()
        result = await processor.process({'key': 'value'})
        assert result.success is True
        assert result.data == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_process_batch(self):
        processor = DataValidationProcessor(config=DataValidationProcessorConfig(batch_size=2))
        items = [{'id': i} for i in range(5)]
        results = await processor.process_batch(items)
        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_pipeline(self):
        pipeline = DataValidationProcessorPipeline()
        pipeline.add_processor(DataValidationProcessor())
        pipeline.add_processor(DataValidationProcessor())
        result = await pipeline.execute({'data': 'test'})
        assert result.success is True

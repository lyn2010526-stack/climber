"""Tests for data_normalization processor."""

import pytest

from app.processors.data_normalization_processor import (
    DataNormalizationProcessor,
    DataNormalizationProcessorConfig,
    DataNormalizationProcessorPipeline,
)


class TestDataNormalizationProcessor:
    """Tests for processor."""

    @pytest.mark.asyncio
    async def test_process(self):
        processor = DataNormalizationProcessor()
        result = await processor.process({'key': 'value'})
        assert result.success is True
        assert result.data == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_process_batch(self):
        processor = DataNormalizationProcessor(config=DataNormalizationProcessorConfig(batch_size=2))
        items = [{'id': i} for i in range(5)]
        results = await processor.process_batch(items)
        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_pipeline(self):
        pipeline = DataNormalizationProcessorPipeline()
        pipeline.add_processor(DataNormalizationProcessor())
        pipeline.add_processor(DataNormalizationProcessor())
        result = await pipeline.execute({'data': 'test'})
        assert result.success is True

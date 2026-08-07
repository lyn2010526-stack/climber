"""Tests for data_cleaning processor."""

import pytest

from app.processors.data_cleaning_processor import (
    DataCleaningProcessor,
    DataCleaningProcessorConfig,
    DataCleaningProcessorPipeline,
)


class TestDataCleaningProcessor:
    """Tests for processor."""

    @pytest.mark.asyncio
    async def test_process(self):
        processor = DataCleaningProcessor()
        result = await processor.process({'key': 'value'})
        assert result.success is True
        assert result.data == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_process_batch(self):
        processor = DataCleaningProcessor(config=DataCleaningProcessorConfig(batch_size=2))
        items = [{'id': i} for i in range(5)]
        results = await processor.process_batch(items)
        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_pipeline(self):
        pipeline = DataCleaningProcessorPipeline()
        pipeline.add_processor(DataCleaningProcessor())
        pipeline.add_processor(DataCleaningProcessor())
        result = await pipeline.execute({'data': 'test'})
        assert result.success is True

"""Tests for data_lineage processor."""

import pytest

from app.processors.data_lineage_processor import (
    DataLineageProcessor,
    DataLineageProcessorConfig,
    DataLineageProcessorPipeline,
)


class TestDataLineageProcessor:
    """Tests for processor."""

    @pytest.mark.asyncio
    async def test_process(self):
        processor = DataLineageProcessor()
        result = await processor.process({'key': 'value'})
        assert result.success is True
        assert result.data == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_process_batch(self):
        processor = DataLineageProcessor(config=DataLineageProcessorConfig(batch_size=2))
        items = [{'id': i} for i in range(5)]
        results = await processor.process_batch(items)
        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_pipeline(self):
        pipeline = DataLineageProcessorPipeline()
        pipeline.add_processor(DataLineageProcessor())
        pipeline.add_processor(DataLineageProcessor())
        result = await pipeline.execute({'data': 'test'})
        assert result.success is True

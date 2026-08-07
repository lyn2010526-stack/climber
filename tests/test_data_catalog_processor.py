"""Tests for data_catalog processor."""

import pytest

from app.processors.data_catalog_processor import (
    DataCatalogProcessor,
    DataCatalogProcessorConfig,
    DataCatalogProcessorPipeline,
)


class TestDataCatalogProcessor:
    """Tests for processor."""

    @pytest.mark.asyncio
    async def test_process(self):
        processor = DataCatalogProcessor()
        result = await processor.process({'key': 'value'})
        assert result.success is True
        assert result.data == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_process_batch(self):
        processor = DataCatalogProcessor(config=DataCatalogProcessorConfig(batch_size=2))
        items = [{'id': i} for i in range(5)]
        results = await processor.process_batch(items)
        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_pipeline(self):
        pipeline = DataCatalogProcessorPipeline()
        pipeline.add_processor(DataCatalogProcessor())
        pipeline.add_processor(DataCatalogProcessor())
        result = await pipeline.execute({'data': 'test'})
        assert result.success is True

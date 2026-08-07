"""Tests for data_enrichment processor."""

import pytest

from app.processors.data_enrichment_processor import (
    DataEnrichmentProcessor,
    DataEnrichmentProcessorConfig,
    DataEnrichmentProcessorPipeline,
)


class TestDataEnrichmentProcessor:
    """Tests for processor."""

    @pytest.mark.asyncio
    async def test_process(self):
        processor = DataEnrichmentProcessor()
        result = await processor.process({'key': 'value'})
        assert result.success is True
        assert result.data == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_process_batch(self):
        processor = DataEnrichmentProcessor(config=DataEnrichmentProcessorConfig(batch_size=2))
        items = [{'id': i} for i in range(5)]
        results = await processor.process_batch(items)
        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_pipeline(self):
        pipeline = DataEnrichmentProcessorPipeline()
        pipeline.add_processor(DataEnrichmentProcessor())
        pipeline.add_processor(DataEnrichmentProcessor())
        result = await pipeline.execute({'data': 'test'})
        assert result.success is True

"""Tests for etl processor."""

import pytest

from app.processors.etl_processor import (
    EtlProcessor,
    EtlProcessorConfig,
    EtlProcessorPipeline,
)


class TestEtlProcessor:
    """Tests for processor."""

    @pytest.mark.asyncio
    async def test_process(self):
        processor = EtlProcessor()
        result = await processor.process({'key': 'value'})
        assert result.success is True
        assert result.data == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_process_batch(self):
        processor = EtlProcessor(config=EtlProcessorConfig(batch_size=2))
        items = [{'id': i} for i in range(5)]
        results = await processor.process_batch(items)
        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_pipeline(self):
        pipeline = EtlProcessorPipeline()
        pipeline.add_processor(EtlProcessor())
        pipeline.add_processor(EtlProcessor())
        result = await pipeline.execute({'data': 'test'})
        assert result.success is True

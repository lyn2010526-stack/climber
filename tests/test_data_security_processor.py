"""Tests for data_security processor."""

import pytest

from app.processors.data_security_processor import (
    DataSecurityProcessor,
    DataSecurityProcessorConfig,
    DataSecurityProcessorPipeline,
)


class TestDataSecurityProcessor:
    """Tests for processor."""

    @pytest.mark.asyncio
    async def test_process(self):
        processor = DataSecurityProcessor()
        result = await processor.process({'key': 'value'})
        assert result.success is True
        assert result.data == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_process_batch(self):
        processor = DataSecurityProcessor(config=DataSecurityProcessorConfig(batch_size=2))
        items = [{'id': i} for i in range(5)]
        results = await processor.process_batch(items)
        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_pipeline(self):
        pipeline = DataSecurityProcessorPipeline()
        pipeline.add_processor(DataSecurityProcessor())
        pipeline.add_processor(DataSecurityProcessor())
        result = await pipeline.execute({'data': 'test'})
        assert result.success is True

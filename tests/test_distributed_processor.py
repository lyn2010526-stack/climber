"""Tests for distributed processor."""

import pytest

from app.processors.distributed_processor import (
    DistributedProcessor,
    DistributedProcessorConfig,
    DistributedProcessorPipeline,
)


class TestDistributedProcessor:
    """Tests for processor."""

    @pytest.mark.asyncio
    async def test_process(self):
        processor = DistributedProcessor()
        result = await processor.process({'key': 'value'})
        assert result.success is True
        assert result.data == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_process_batch(self):
        processor = DistributedProcessor(config=DistributedProcessorConfig(batch_size=2))
        items = [{'id': i} for i in range(5)]
        results = await processor.process_batch(items)
        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_pipeline(self):
        pipeline = DistributedProcessorPipeline()
        pipeline.add_processor(DistributedProcessor())
        pipeline.add_processor(DistributedProcessor())
        result = await pipeline.execute({'data': 'test'})
        assert result.success is True

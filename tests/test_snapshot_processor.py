"""Tests for snapshot processor."""

import pytest

from app.processors.snapshot_processor import (
    SnapshotProcessor,
    SnapshotProcessorConfig,
    SnapshotProcessorPipeline,
)


class TestSnapshotProcessor:
    """Tests for processor."""

    @pytest.mark.asyncio
    async def test_process(self):
        processor = SnapshotProcessor()
        result = await processor.process({'key': 'value'})
        assert result.success is True
        assert result.data == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_process_batch(self):
        processor = SnapshotProcessor(config=SnapshotProcessorConfig(batch_size=2))
        items = [{'id': i} for i in range(5)]
        results = await processor.process_batch(items)
        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_pipeline(self):
        pipeline = SnapshotProcessorPipeline()
        pipeline.add_processor(SnapshotProcessor())
        pipeline.add_processor(SnapshotProcessor())
        result = await pipeline.execute({'data': 'test'})
        assert result.success is True

"""Tests for data_governance processor."""

import pytest

from app.processors.data_governance_processor import (
    DataGovernanceProcessor,
    DataGovernanceProcessorConfig,
    DataGovernanceProcessorPipeline,
)


class TestDataGovernanceProcessor:
    """Tests for processor."""

    @pytest.mark.asyncio
    async def test_process(self):
        processor = DataGovernanceProcessor()
        result = await processor.process({'key': 'value'})
        assert result.success is True
        assert result.data == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_process_batch(self):
        processor = DataGovernanceProcessor(config=DataGovernanceProcessorConfig(batch_size=2))
        items = [{'id': i} for i in range(5)]
        results = await processor.process_batch(items)
        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_pipeline(self):
        pipeline = DataGovernanceProcessorPipeline()
        pipeline.add_processor(DataGovernanceProcessor())
        pipeline.add_processor(DataGovernanceProcessor())
        result = await pipeline.execute({'data': 'test'})
        assert result.success is True

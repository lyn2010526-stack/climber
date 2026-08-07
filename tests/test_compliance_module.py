"""Tests for compliance."""

import pytest

from app.modules.compliance_module import (
    ComplianceManager,
    ComplianceType,
)


class TestComplianceManager:
    """Tests for manager."""

    @pytest.mark.asyncio
    async def test_create_and_get(self):
        manager = ComplianceManager()
        await manager.initialize()
        item = await manager.create('test', ComplianceType.TYPE_A)
        assert item.name == 'test'
        found = await manager.get(item.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_update(self):
        manager = ComplianceManager()
        item = await manager.create('test', ComplianceType.TYPE_A)
        updated = await manager.update(item.id, name='updated')
        assert updated is not None
        assert updated.name == 'updated'

    @pytest.mark.asyncio
    async def test_delete(self):
        manager = ComplianceManager()
        item = await manager.create('test', ComplianceType.TYPE_A)
        result = await manager.delete(item.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_items(self):
        manager = ComplianceManager()
        await manager.create('a', ComplianceType.TYPE_A)
        await manager.create('b', ComplianceType.TYPE_B)
        result = await manager.list_items()
        assert result.total == 2

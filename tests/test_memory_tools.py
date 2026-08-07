"""Tests for memory tools."""

from __future__ import annotations

import unittest.mock as mock

import pytest

from app.tools import memory_tools


class TestStoreMemory:
    """Tests for store_memory."""

    @pytest.mark.asyncio
    async def test_store_memory_success(self):
        mock_mem = mock.MagicMock()
        mock_mem.id = "mem-123"

        with mock.patch.object(memory_tools, "persistent_memory") as mock_pm:
            mock_pm.create_episodic_memory = mock.AsyncMock(return_value=mock_mem)
            result = await memory_tools.store_memory("User likes Python", 0.8, "preference")

        assert "Memory stored" in result
        assert "mem-123" in result

    @pytest.mark.asyncio
    async def test_store_memory_empty_content(self):
        result = await memory_tools.store_memory("")
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_store_memory_exception(self):
        with mock.patch.object(memory_tools, "persistent_memory") as mock_pm:
            mock_pm.create_episodic_memory = mock.AsyncMock(side_effect=Exception("DB error"))
            result = await memory_tools.store_memory("Test memory")

        assert "Error" in result


class TestSearchMemories:
    """Tests for search_memories."""

    @pytest.mark.asyncio
    async def test_search_memories_success(self):
        mock_mem = mock.MagicMock()
        mock_mem.memory_type = "preference"
        mock_mem.content = "User likes Python"

        with mock.patch.object(memory_tools, "persistent_memory") as mock_pm:
            mock_pm.retrieve_memories = mock.AsyncMock(return_value=[mock_mem])
            result = await memory_tools.search_memories("Python")

        assert "Found 1 memories" in result
        assert "User likes Python" in result

    @pytest.mark.asyncio
    async def test_search_memories_empty_query(self):
        result = await memory_tools.search_memories("")
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_search_memories_no_results(self):
        with mock.patch.object(memory_tools, "persistent_memory") as mock_pm:
            mock_pm.retrieve_memories = mock.AsyncMock(return_value=[])
            result = await memory_tools.search_memories("nonexistent")

        assert "No memories found" in result

    @pytest.mark.asyncio
    async def test_search_memories_exception(self):
        with mock.patch.object(memory_tools, "persistent_memory") as mock_pm:
            mock_pm.retrieve_memories = mock.AsyncMock(side_effect=Exception("DB error"))
            result = await memory_tools.search_memories("test")

        assert "Error" in result


class TestRememberUserFact:
    """Tests for remember_user_fact."""

    @pytest.mark.asyncio
    async def test_remember_fact_success(self):
        with mock.patch.object(memory_tools, "persistent_memory") as mock_pm:
            mock_pm.add_user_fact = mock.AsyncMock(return_value=mock.MagicMock())
            result = await memory_tools.remember_user_fact("User is a developer", "work")

        assert "remembered" in result
        assert "work" in result

    @pytest.mark.asyncio
    async def test_remember_fact_empty(self):
        result = await memory_tools.remember_user_fact("")
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_remember_fact_exception(self):
        with mock.patch.object(memory_tools, "persistent_memory") as mock_pm:
            mock_pm.add_user_fact = mock.AsyncMock(side_effect=Exception("DB error"))
            result = await memory_tools.remember_user_fact("Test fact")

        assert "Error" in result

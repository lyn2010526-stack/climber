"""Tests for the enhanced parallel tool executor."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.parallel_enhanced import EnhancedParallelToolExecutor


@pytest.fixture
def mock_registry():
    registry = AsyncMock()
    registry.execute = AsyncMock(return_value="result")
    return registry


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.session_id = "test-session"
    session._stop_requested = False
    return session


@pytest.fixture
def mock_event_bus():
    bus = AsyncMock()
    bus.publish = AsyncMock()
    return bus


class TestEnhancedParallelToolExecutor:
    @pytest.mark.asyncio
    async def test_execute_all_empty(self, mock_registry, mock_session, mock_event_bus):
        executor = EnhancedParallelToolExecutor(
            mock_registry, session=mock_session, event_bus=mock_event_bus,
        )
        results = await executor.execute_all([])
        assert results == []

    @pytest.mark.asyncio
    async def test_execute_all_single_tool(self, mock_registry, mock_session, mock_event_bus):
        executor = EnhancedParallelToolExecutor(
            mock_registry, session=mock_session, event_bus=mock_event_bus,
        )
        tool_calls = [{
            "id": "call_1",
            "function": {"name": "test_tool", "arguments": {"key": "value"}},
        }]
        results = await executor.execute_all(tool_calls)
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].tool_name == "test_tool"

    @pytest.mark.asyncio
    async def test_execute_all_multiple_tools(self, mock_registry, mock_session, mock_event_bus):
        executor = EnhancedParallelToolExecutor(
            mock_registry, session=mock_session, event_bus=mock_event_bus,
        )
        tool_calls = [
            {"id": f"call_{i}", "function": {"name": f"tool_{i}", "arguments": {}}}
            for i in range(5)
        ]
        results = await executor.execute_all(tool_calls)
        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_concurrency_limit_read_only(self, mock_registry, mock_session, mock_event_bus):
        executor = EnhancedParallelToolExecutor(
            mock_registry, session=mock_session, event_bus=mock_event_bus,
        )
        tool_names = ["read_file", "grep", "glob", "list_directory"]
        limit = executor._get_concurrency_limit(tool_names)
        assert limit == 20  # High concurrency for read-only tools

    @pytest.mark.asyncio
    async def test_concurrency_limit_mixed(self, mock_registry, mock_session, mock_event_bus):
        executor = EnhancedParallelToolExecutor(
            mock_registry, session=mock_session, event_bus=mock_event_bus,
        )
        tool_names = ["read_file", "write_file"]
        limit = executor._get_concurrency_limit(tool_names)
        assert limit == 3  # Low concurrency when write tools present

    @pytest.mark.asyncio
    async def test_timeout_adaptive(self, mock_registry, mock_session, mock_event_bus):
        executor = EnhancedParallelToolExecutor(
            mock_registry, session=mock_session, event_bus=mock_event_bus,
            timeout_per_tool=30.0,
        )
        # Long-running tool gets 3x timeout
        timeout = executor._get_timeout_for_tool("run_command")
        assert timeout == 90.0

        # Normal tool gets default timeout
        timeout = executor._get_timeout_for_tool("read_file")
        assert timeout == 30.0

    @pytest.mark.asyncio
    async def test_event_bus_emission(self, mock_registry, mock_session, mock_event_bus):
        executor = EnhancedParallelToolExecutor(
            mock_registry, session=mock_session, event_bus=mock_event_bus,
        )
        tool_calls = [{
            "id": "call_1",
            "function": {"name": "test_tool", "arguments": {}},
        }]
        await executor.execute_all(tool_calls)

        # Verify events were published
        assert mock_event_bus.publish.call_count >= 2  # start + complete

    @pytest.mark.asyncio
    async def test_execute_one_timeout(self, mock_registry, mock_session, mock_event_bus):
        mock_registry.execute = AsyncMock(side_effect=asyncio.TimeoutError)
        executor = EnhancedParallelToolExecutor(
            mock_registry, session=mock_session, event_bus=mock_event_bus,
            timeout_per_tool=0.1,
        )
        result = await executor._execute_one("test_tool", {})
        assert result.success is False
        assert "timeout" in result.error.lower()

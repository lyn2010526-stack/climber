"""Tests for MCP controller."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.mcp_controller import McpController, McpStatus


@pytest.fixture
def mcp_controller():
    return McpController(startup_timeout=1, max_restarts=3)


class TestMcpController:
    def test_initial_status(self, mcp_controller):
        """Initial status should be disconnected."""
        assert mcp_controller.status == McpStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_start_success(self, mcp_controller):
        """Test successful start."""
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process

            with patch('asyncio.sleep'):
                result = await mcp_controller.start()

            assert result.success is True
            assert result.status == McpStatus.READY
            assert mcp_controller.status == McpStatus.READY

    @pytest.mark.asyncio
    async def test_start_timeout(self, mcp_controller):
        """Test start timeout."""
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process

            with patch('asyncio.sleep', side_effect=TimeoutError()):
                result = await mcp_controller.start()

            assert result.success is False
            assert result.status == McpStatus.ERROR
            assert "超时" in result.error

    @pytest.mark.asyncio
    async def test_start_failure(self, mcp_controller):
        """Test start failure."""
        with patch('subprocess.Popen', side_effect=RuntimeError("test error")):
            result = await mcp_controller.start()

        assert result.success is False
        assert result.status == McpStatus.ERROR
        assert "test error" in result.error

    @pytest.mark.asyncio
    async def test_restart_success(self, mcp_controller):
        """Test successful restart."""
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process

            with patch('asyncio.sleep'):
                await mcp_controller.start()
                await mcp_controller.stop()
                result = await mcp_controller.restart()

            assert result.success is True
            assert result.status == McpStatus.READY

    @pytest.mark.asyncio
    async def test_max_restarts_limit(self, mcp_controller):
        """Test max restarts limit."""
        mcp_controller.restart_count = 3
        result = await mcp_controller.restart()

        assert result.success is False
        assert result.status == McpStatus.ERROR
        assert "上限" in result.error

    @pytest.mark.asyncio
    async def test_health_check_disconnected(self, mcp_controller):
        """Test health check when disconnected."""
        status = await mcp_controller.health_check()
        assert status == McpStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_health_check_running(self, mcp_controller):
        """Test health check when process is running."""
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process

            with patch('asyncio.sleep'):
                await mcp_controller.start()
                status = await mcp_controller.health_check()

            assert status == McpStatus.READY

    @pytest.mark.asyncio
    async def test_health_check_crashed(self, mcp_controller):
        """Test health check when process crashed."""
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.poll.return_value = 1
            mock_popen.return_value = mock_process

            with patch('asyncio.sleep'):
                await mcp_controller.start()
                status = await mcp_controller.health_check()

            assert status == McpStatus.ERROR

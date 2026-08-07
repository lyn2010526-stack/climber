"""Tests for vision tools."""

from __future__ import annotations

import unittest.mock as mock

import pytest

from app.tools import vision_tools


class TestCaptureScreen:
    """Tests for capture_screen."""

    @pytest.mark.asyncio
    async def test_capture_screen_success(self):
        mock_result = mock.MagicMock()
        mock_result.success = True
        mock_result.metadata = {"base64": "iVBORw0KGgo="}

        with mock.patch.object(vision_tools, "vision_pipeline") as mock_pipeline:
            mock_pipeline.capture_screen = mock.AsyncMock(return_value=mock_result)
            result = await vision_tools.capture_screen()

        assert "data:image/png;base64," in result
        assert "iVBORw0KGgo=" in result

    @pytest.mark.asyncio
    async def test_capture_screen_failure(self):
        mock_result = mock.MagicMock()
        mock_result.success = False
        mock_result.error = "Screen capture failed"

        with mock.patch.object(vision_tools, "vision_pipeline") as mock_pipeline:
            mock_pipeline.capture_screen = mock.AsyncMock(return_value=mock_result)
            result = await vision_tools.capture_screen()

        assert "Error" in result

    @pytest.mark.asyncio
    async def test_capture_screen_exception(self):
        with mock.patch.object(vision_tools, "vision_pipeline") as mock_pipeline:
            mock_pipeline.capture_screen = mock.AsyncMock(side_effect=Exception("Failed"))
            result = await vision_tools.capture_screen()

        assert "Error" in result

    @pytest.mark.asyncio
    async def test_capture_screen_with_region(self):
        mock_result = mock.MagicMock()
        mock_result.success = True
        mock_result.metadata = {"base64": "test"}

        with mock.patch.object(vision_tools, "vision_pipeline") as mock_pipeline:
            mock_pipeline.capture_screen = mock.AsyncMock(return_value=mock_result)
            await vision_tools.capture_screen(source="native", region=[0, 0, 100, 100])

        mock_pipeline.capture_screen.assert_called_once_with(
            source="native", region=(0, 0, 100, 100), session_id="default"
        )


class TestOcrScreen:
    """Tests for ocr_screen."""

    @pytest.mark.asyncio
    async def test_ocr_screen_success(self):
        mock_result = mock.MagicMock()
        mock_result.success = True
        mock_result.content = "Hello World"

        with mock.patch.object(vision_tools, "vision_pipeline") as mock_pipeline:
            mock_pipeline.ocr_screen = mock.AsyncMock(return_value=mock_result)
            result = await vision_tools.ocr_screen()

        assert "Hello World" in result

    @pytest.mark.asyncio
    async def test_ocr_screen_failure(self):
        mock_result = mock.MagicMock()
        mock_result.success = False
        mock_result.error = "OCR failed"

        with mock.patch.object(vision_tools, "vision_pipeline") as mock_pipeline:
            mock_pipeline.ocr_screen = mock.AsyncMock(return_value=mock_result)
            result = await vision_tools.ocr_screen()

        assert "Error" in result


class TestDescribeScreen:
    """Tests for describe_screen."""

    @pytest.mark.asyncio
    async def test_describe_screen_success(self):
        mock_result = mock.MagicMock()
        mock_result.success = True
        mock_result.content = "A window with text"

        with mock.patch.object(vision_tools, "vision_pipeline") as mock_pipeline:
            mock_pipeline.describe_screen = mock.AsyncMock(return_value=mock_result)
            result = await vision_tools.describe_screen()

        assert "A window with text" in result

    @pytest.mark.asyncio
    async def test_describe_screen_failure(self):
        mock_result = mock.MagicMock()
        mock_result.success = False
        mock_result.error = "Description failed"

        with mock.patch.object(vision_tools, "vision_pipeline") as mock_pipeline:
            mock_pipeline.describe_screen = mock.AsyncMock(return_value=mock_result)
            result = await vision_tools.describe_screen()

        assert "Error" in result


class TestFindAndClick:
    """Tests for find_and_click."""

    @pytest.mark.asyncio
    async def test_find_and_click_success(self):
        mock_result = mock.MagicMock()
        mock_result.success = True
        mock_result.content = "Clicked Submit"

        with mock.patch.object(vision_tools, "vision_pipeline") as mock_pipeline:
            mock_pipeline.find_and_click = mock.AsyncMock(return_value=mock_result)
            result = await vision_tools.find_and_click("Submit")

        assert isinstance(result, str)
        assert "Clicked" in result

    @pytest.mark.asyncio
    async def test_find_and_click_failure(self):
        mock_result = mock.MagicMock()
        mock_result.success = False
        mock_result.error = "Not found"

        with mock.patch.object(vision_tools, "vision_pipeline") as mock_pipeline:
            mock_pipeline.find_and_click = mock.AsyncMock(return_value=mock_result)
            result = await vision_tools.find_and_click("Nonexistent")

        assert "Error" in result


class TestFindAndType:
    """Tests for find_and_type."""

    @pytest.mark.asyncio
    async def test_find_and_type_success(self):
        mock_result = mock.MagicMock()
        mock_result.success = True
        mock_result.content = "Typed into field"

        with mock.patch.object(vision_tools, "vision_pipeline") as mock_pipeline:
            mock_pipeline.find_and_type = mock.AsyncMock(return_value=mock_result)
            result = await vision_tools.find_and_type("Username", "admin")

        assert isinstance(result, str)
        assert "Typed" in result

    @pytest.mark.asyncio
    async def test_find_and_type_failure(self):
        mock_result = mock.MagicMock()
        mock_result.success = False
        mock_result.error = "Field not found"

        with mock.patch.object(vision_tools, "vision_pipeline") as mock_pipeline:
            mock_pipeline.find_and_type = mock.AsyncMock(return_value=mock_result)
            result = await vision_tools.find_and_type("Nonexistent", "text")

        assert "Error" in result

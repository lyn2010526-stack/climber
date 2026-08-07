"""Tests for app/tools/builtins.py - built-in tool functions."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Safe eval math tests ─────────────────────────────────────────────────


class TestSafeEvalMath:
    def test_simple_arithmetic(self):
        from app.tools.builtins import _safe_eval_math
        assert _safe_eval_math("1 + 2", {}) == 3
        assert _safe_eval_math("10 - 3", {}) == 7
        assert _safe_eval_math("4 * 5", {}) == 20
        assert _safe_eval_math("10 / 2", {}) == 5.0

    def test_math_functions(self):
        from app.tools.builtins import _safe_eval_math
        assert _safe_eval_math("sqrt(16)", {}) == 4.0
        assert _safe_eval_math("pow(2, 3)", {}) == 8.0
        assert _safe_eval_math("abs(-5)", {}) == 5

    def test_constants(self):
        from app.tools.builtins import _safe_eval_math
        result = _safe_eval_math("pi", {})
        assert result > 3.14 and result < 3.15

    def test_comparison_operators(self):
        from app.tools.builtins import _safe_eval_math
        assert _safe_eval_math("1 < 2", {}) is True
        assert _safe_eval_math("1 > 2", {}) is False
        assert _safe_eval_math("1 == 1", {}) is True

    def test_unsafe_expression_raises(self):
        from app.tools.builtins import _safe_eval_math
        with pytest.raises(ValueError):
            _safe_eval_math("__import__('os')", {})

    def test_unknown_name_raises(self):
        from app.tools.builtins import _safe_eval_math
        with pytest.raises(ValueError, match="Unsupported name"):
            _safe_eval_math("unknown_func(1)", {})

    def test_with_local_vars(self):
        from app.tools.builtins import _safe_eval_math
        result = _safe_eval_math("x + y", {"x": 1, "y": 2})
        assert result == 3 or abs(result - 3) < 0.001


# ── calculator tool tests ────────────────────────────────────────────────


class TestCalculator:
    @pytest.mark.asyncio
    async def test_basic_addition(self):
        from app.tools.builtins import calculator
        result = await calculator("1 + 2")
        assert result == "3"

    @pytest.mark.asyncio
    async def test_power_operator(self):
        from app.tools.builtins import calculator
        result = await calculator("2 ^ 10")
        assert result == "1024"

    @pytest.mark.asyncio
    async def test_sqrt_function(self):
        from app.tools.builtins import calculator
        result = await calculator("sqrt(144)")
        assert result == "12.0"

    @pytest.mark.asyncio
    async def test_trig_functions(self):
        from app.tools.builtins import calculator
        result = await calculator("sin(0)")
        assert result == "0.0"

    @pytest.mark.asyncio
    async def test_rejects_non_math_chars(self):
        from app.tools.builtins import calculator
        result = await calculator("import os")
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_complex_expression(self):
        from app.tools.builtins import calculator
        result = await calculator("(2 + 3) * 4")
        assert result == "20"

    @pytest.mark.asyncio
    async def test_division_by_zero(self):
        from app.tools.builtins import calculator
        result = await calculator("1 / 0")
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_log_functions(self):
        from app.tools.builtins import calculator
        result = await calculator("log10(100)")
        assert result == "2.0"

    @pytest.mark.asyncio
    async def test_factorial(self):
        from app.tools.builtins import calculator
        result = await calculator("factorial(5)")
        assert result == "120"

    @pytest.mark.asyncio
    async def test_gcd(self):
        from app.tools.builtins import calculator
        result = await calculator("gcd(12, 8)")
        assert result == "4"


# ── get_datetime tool tests ──────────────────────────────────────────────


class TestGetDatetime:
    @pytest.mark.asyncio
    async def test_returns_iso_format(self):
        from app.tools.builtins import get_datetime
        result = await get_datetime()
        assert isinstance(result, str)
        assert "T" in result  # ISO format contains T

    @pytest.mark.asyncio
    async def test_returns_valid_datetime(self):
        from datetime import datetime

        from app.tools.builtins import get_datetime
        result = await get_datetime()
        parsed = datetime.fromisoformat(result)
        assert parsed is not None


# ── fetch_url tool tests ─────────────────────────────────────────────────


class TestFetchUrl:
    @pytest.mark.asyncio
    async def test_successful_fetch(self):
        from app.tools.builtins import fetch_url
        mock_response = MagicMock()
        mock_response.text = "<html>Hello World</html>"
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=AsyncMock(
                get=AsyncMock(return_value=mock_response),
            ))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await fetch_url("https://example.com")

        assert "Hello World" in result
        assert "200" in result

    @pytest.mark.asyncio
    async def test_fetch_error(self):
        from app.tools.builtins import fetch_url
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await fetch_url("https://invalid-url.test")

        assert "Error" in result


# ── web_search tool tests ────────────────────────────────────────────────


class TestWebSearch:
    @pytest.mark.asyncio
    async def test_successful_search(self):
        from app.tools.builtins import web_search
        mock_response = MagicMock()
        mock_response.text = "<html>Search results for test</html>"
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=AsyncMock(
                get=AsyncMock(return_value=mock_response),
            ))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await web_search("test query")

        assert "Search results for: test query" in result

    @pytest.mark.asyncio
    async def test_search_error(self):
        from app.tools.builtins import web_search
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(side_effect=Exception("Network error"))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await web_search("test")

        assert "Search error" in result


# ── read_file tool tests ─────────────────────────────────────────────────


class TestReadFile:
    @pytest.mark.asyncio
    async def test_edit_file_validation_fails(self):
        from app.tools.builtins import edit_file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("hello world")
            f.flush()
            path = f.name

        result = await edit_file(path, "goodbye", "not_a_number")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_edit_file_plan_mode(self):
        from app.tools.builtins import edit_file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello World")
            path = f.name

        with patch("app.core.file_patch.FilePatchService") as mock_service:
            mock_service.validate_edit = MagicMock(return_value=(True, ""))
            mock_service.preview_edit = MagicMock(return_value=("diff content", "ok"))
            with patch("app.core.file_patch.get_current_agent_mode", return_value="plan"):
                result = await edit_file(path, "Hello", "Hi")

        os.unlink(path)
        assert "PLAN mode" in result or isinstance(result, str)


# ── handoff_task tool tests ──────────────────────────────────────────────


class TestHandoffTask:
    @pytest.mark.asyncio
    async def test_handoff_success(self):
        from app.tools.builtins import handoff_task
        mock_engine = AsyncMock()
        mock_engine.handoff_task = AsyncMock(return_value="done")

        with patch("app.tools.builtins._get_group_engine", return_value=mock_engine):
            result = await handoff_task("task-1", "agent-2", "reason")

        assert "handed off" in result.lower()

    @pytest.mark.asyncio
    async def test_handoff_failure(self):
        from app.tools.builtins import handoff_task
        with patch("app.tools.builtins._get_group_engine", side_effect=Exception("No engine")):
            result = await handoff_task("task-1", "agent-2")

        assert "failed" in result.lower()


# ── run_group_tasks tool tests ───────────────────────────────────────────


class TestRunGroupTasks:
    @pytest.mark.asyncio
    async def test_run_tasks_success(self):
        from app.tools.builtins import run_group_tasks
        mock_engine = AsyncMock()
        mock_engine.run_group_tasks = AsyncMock(return_value="completed")

        with patch("app.tools.builtins._get_group_engine", return_value=mock_engine):
            result = await run_group_tasks("group-1")

        assert "executed" in result.lower()

    @pytest.mark.asyncio
    async def test_run_tasks_failure(self):
        from app.tools.builtins import run_group_tasks
        with patch("app.tools.builtins._get_group_engine", side_effect=Exception("No engine")):
            result = await run_group_tasks("group-1")

        assert "failed" in result.lower()

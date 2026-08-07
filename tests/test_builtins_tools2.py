"""Tests for built-in tools - part 2."""

from __future__ import annotations

import os
import tempfile

import pytest

from app.tools.builtins import (
    _safe_eval_math,
    analyze_error,
    append_file,
    apply_patch,
    container_exec,
    edit_file,
    file_diff,
    file_exists,
    file_info,
    generate_image,
    get_datetime,
    get_weather,
    handoff_task,
    list_files,
    read_file,
    run_group_tasks,
    stream_command,
    suggest_fix,
    translate,
    wikipedia_summary,
    write_file,
)


class TestSafeEvalMathExtended:
    """Extended tests for _safe_eval_math."""

    def test_trigonometric_functions(self):
        result = _safe_eval_math("sin(0)", {})
        assert result == 0.0

    def test_logarithm(self):
        result = _safe_eval_math("log(e)", {})
        assert result == 1.0

    def test_sqrt(self):
        result = _safe_eval_math("sqrt(16)", {})
        assert result == 4.0

    def test_complex_expression(self):
        result = _safe_eval_math("sqrt(9) + pow(2, 3)", {})
        assert result == 11.0

    def test_constants(self):
        result = _safe_eval_math("pi", {})
        assert result > 3.14

    def test_invalid_name_raises(self):
        with pytest.raises(ValueError):
            _safe_eval_math("undefined_var + 1", {})


class TestGetDateTime:
    """Tests for get_datetime."""

    @pytest.mark.asyncio
    async def test_returns_iso_format(self):
        result = await get_datetime()
        assert isinstance(result, str)
        assert "T" in result or "-" in result


class TestGetWeather:
    """Tests for get_weather."""

    @pytest.mark.asyncio
    async def test_returns_string(self):
        result = await get_weather("London")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_city_in_response(self):
        result = await get_weather("London")
        assert "London" in result or "weather" in result.lower() or "error" in result.lower()


class TestReadFile:
    """Tests for read_file."""

    @pytest.mark.asyncio
    async def test_read_existing_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test content")
            f.flush()
            result = await read_file(f.name)
            assert result == "test content"
        os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self):
        result = await read_file("/nonexistent/file.txt")
        assert "error" in result.lower() or "not found" in result.lower()


class TestWriteFile:
    """Tests for write_file."""

    @pytest.mark.asyncio
    async def test_write_new_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            path = f.name
        os.unlink(path)
        result = await write_file(path, "hello world")
        assert "success" in result.lower() or "written" in result.lower()
        with open(path) as f:
            assert f.read() == "hello world"
        os.unlink(path)

    @pytest.mark.asyncio
    async def test_write_overwrites_existing(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("old content")
            f.flush()
            await write_file(f.name, "new content")
            with open(f.name) as rf:
                assert rf.read() == "new content"
        os.unlink(f.name)


class TestListFiles:
    """Tests for list_files."""

    @pytest.mark.asyncio
    async def test_list_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "test.txt"), 'w').close()
            result = await list_files(tmpdir)
            assert "test.txt" in result

    @pytest.mark.asyncio
    async def test_list_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await list_files(tmpdir)
            assert isinstance(result, str)


class TestStreamCommand:
    """Tests for stream_command."""

    @pytest.mark.asyncio
    async def test_stream_echo(self):
        result = await stream_command("echo hello", timeout=5)
        assert isinstance(result, str)


class TestGenerateImage:
    """Tests for generate_image."""

    @pytest.mark.asyncio
    async def test_returns_string(self):
        result = await generate_image("a cat")
        assert isinstance(result, str)


class TestTranslate:
    """Tests for translate."""

    @pytest.mark.asyncio
    async def test_returns_string(self):
        result = await translate("hello", "es")
        assert isinstance(result, str)


class TestWikipediaSummary:
    """Tests for wikipedia_summary."""

    @pytest.mark.asyncio
    async def test_returns_string(self):
        result = await wikipedia_summary("Python")
        assert isinstance(result, str)


class TestEditFile:
    """Tests for edit_file."""

    @pytest.mark.asyncio
    async def test_edit_existing_content(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, dir=os.getcwd()) as f:
            f.write("hello world")
            f.flush()
            result = await edit_file(f.name, "hello", "hi")
            assert isinstance(result, str)
        os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_edit_nonexistent_content(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, dir=os.getcwd()) as f:
            f.write("hello")
            f.flush()
            result = await edit_file(f.name, "nonexistent", "replacement")
            assert isinstance(result, str)
        os.unlink(f.name)


class TestFileDiff:
    """Tests for file_diff."""

    @pytest.mark.asyncio
    async def test_diff_shows_changes(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("old line")
            f.flush()
            result = await file_diff(f.name, "new line")
            assert "old" in result or "new" in result or "-" in result or "+" in result
        os.unlink(f.name)


class TestAppendFile:
    """Tests for append_file."""

    @pytest.mark.asyncio
    async def test_append_to_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("first")
            f.flush()
            await append_file(f.name, "second")
            with open(f.name) as rf:
                content = rf.read()
                assert "first" in content and "second" in content
        os.unlink(f.name)


class TestFileExists:
    """Tests for file_exists."""

    @pytest.mark.asyncio
    async def test_existing_file(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"data")
            f.flush()
            result = await file_exists(f.name)
            assert "exists" in result.lower() or "true" in result.lower()
        os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_nonexistent_file(self):
        result = await file_exists("/nonexistent/file.txt")
        assert "not found" in result.lower() or "false" in result.lower() or "not exist" in result.lower()


class TestFileInfo:
    """Tests for file_info."""

    @pytest.mark.asyncio
    async def test_returns_file_info(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test data")
            f.flush()
            result = await file_info(f.name)
            assert isinstance(result, str)
            assert len(result) > 0
        os.unlink(f.name)


class TestHandoffTask:
    """Tests for handoff_task."""

    @pytest.mark.asyncio
    async def test_returns_string(self):
        result = await handoff_task("task-1", "agent-2", "reason")
        assert isinstance(result, str)


class TestRunGroupTasks:
    """Tests for run_group_tasks."""

    @pytest.mark.asyncio
    async def test_returns_string(self):
        result = await run_group_tasks("group-1")
        assert isinstance(result, str)


class TestApplyPatch:
    """Tests for apply_patch."""

    @pytest.mark.asyncio
    async def test_patch_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("line1\nline2\nline3\n")
            f.flush()
            patch = "--- a/file\n+++ b/file\n@@ -1,3 +1,3 @@\n line1\n-line2\n+modified\n line3"
            result = await apply_patch(f.name, patch)
            assert isinstance(result, str)
        os.unlink(f.name)


class TestStreamCommand:
    """Tests for stream_command."""

    @pytest.mark.asyncio
    async def test_stream_echo(self):
        result = await stream_command("echo hello", timeout=5)
        assert isinstance(result, str)


class TestContainerExec:
    """Tests for container_exec."""

    @pytest.mark.asyncio
    async def test_returns_string(self):
        result = await container_exec("container-1", "ls")
        assert isinstance(result, str)


class TestAnalyzeErrorExtended:
    """Extended tests for analyze_error."""

    @pytest.mark.asyncio
    async def test_runtime_error(self):
        result = await analyze_error("RuntimeError: division by zero")
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_empty_error(self):
        result = await analyze_error("")
        assert isinstance(result, str)


class TestAnalyzeError:
    """Tests for analyze_error."""

    @pytest.mark.asyncio
    async def test_returns_analysis(self):
        result = await analyze_error("SyntaxError: unexpected indent")
        assert isinstance(result, str)
        assert len(result) > 0


class TestSuggestFix:
    """Tests for suggest_fix."""

    @pytest.mark.asyncio
    async def test_returns_suggestion(self):
        result = await suggest_fix("SyntaxError in line 5")
        assert isinstance(result, str)
        assert len(result) > 0

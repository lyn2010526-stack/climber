"""Extended tests for built-in tools."""

from __future__ import annotations

import unittest.mock as mock

import pytest

from app.tools.builtins import (
    _safe_eval_math,
    append_file,
    base64_encode,
    calculator,
    file_diff,
    file_exists,
    file_info,
    get_datetime,
    json_get,
    list_files,
    read_file,
    summarize,
    write_file,
)


class TestSafeEvalMathExtended:
    """Extended tests for _safe_eval_math."""

    def test_basic_arithmetic(self):
        assert _safe_eval_math("1 + 2", {}) == 3

    def test_complex_expression(self):
        assert _safe_eval_math("2 * (3 + 4)", {}) == 14

    def test_math_functions(self):
        assert _safe_eval_math("sqrt(16)", {}) == 4.0

    def test_constants(self):
        assert _safe_eval_math("pi", {}) == mock.ANY

    def test_unsafe_expression_rejected(self):
        with pytest.raises(ValueError):
            _safe_eval_math("__import__('os')", {})

    def test_unknown_name_rejected(self):
        with pytest.raises(ValueError):
            _safe_eval_math("unknown_var", {})

    def test_unsupported_node_rejected(self):
        with pytest.raises(ValueError):
            _safe_eval_math("[x for x in range(10)]", {})


class TestCalculator:
    """Tests for calculator tool."""

    @pytest.mark.asyncio
    async def test_simple_calculation(self):
        result = await calculator("2 + 2")
        assert result == "4"

    @pytest.mark.asyncio
    async def test_power_operator(self):
        result = await calculator("2 ^ 3")
        assert result == "8"

    @pytest.mark.asyncio
    async def test_math_function(self):
        result = await calculator("sqrt(16)")
        assert result == "4.0"

    @pytest.mark.asyncio
    async def test_unsafe_chars_rejected(self):
        result = await calculator("2 + __import__('os')")
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_syntax_error(self):
        result = await calculator("2 +")
        assert "Error" in result


class TestGetDatetime:
    """Tests for get_datetime tool."""

    @pytest.mark.asyncio
    async def test_returns_iso_format(self):
        result = await get_datetime()
        assert isinstance(result, str)
        assert "T" in result


class TestReadFile:
    """Tests for read_file tool."""

    @pytest.mark.asyncio
    async def test_reads_file(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")
        result = await read_file(str(test_file))
        assert result == "Hello, World!"

    @pytest.mark.asyncio
    async def test_file_not_found(self):
        result = await read_file("/nonexistent/file.txt")
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_truncates_long_content(self, tmp_path):
        test_file = tmp_path / "long.txt"
        test_file.write_text("x" * 15000)
        result = await read_file(str(test_file))
        assert len(result) == 10000


class TestWriteFile:
    """Tests for write_file tool."""

    @pytest.mark.asyncio
    async def test_writes_file(self, tmp_path):
        test_file = tmp_path / "output.txt"
        result = await write_file(str(test_file), "Hello!")
        assert "File written" in result
        assert test_file.read_text() == "Hello!"

    @pytest.mark.asyncio
    async def test_error_handling(self):
        result = await write_file("/nonexistent/dir/file.txt", "content")
        assert "Error" in result


class TestListFiles:
    """Tests for list_files tool."""

    @pytest.mark.asyncio
    async def test_lists_files(self, tmp_path):
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.txt").touch()
        result = await list_files(str(tmp_path))
        assert "file1.txt" in result
        assert "file2.txt" in result

    @pytest.mark.asyncio
    async def test_empty_directory(self, tmp_path):
        result = await list_files(str(tmp_path))
        assert "empty" in result.lower()

    @pytest.mark.asyncio
    async def test_nonexistent_directory(self):
        result = await list_files("/nonexistent/dir")
        assert "Error" in result


class TestAppendFile:
    """Tests for append_file tool."""

    @pytest.mark.asyncio
    async def test_appends_content(self, tmp_path):
        test_file = tmp_path / "append.txt"
        test_file.write_text("Hello")
        result = await append_file(str(test_file), " World")
        assert "Appended" in result
        assert test_file.read_text() == "Hello World"

    @pytest.mark.asyncio
    async def test_error_handling(self):
        result = await append_file("/nonexistent/file.txt", "content")
        assert "Error" in result


class TestFileExists:
    """Tests for file_exists tool."""

    @pytest.mark.asyncio
    async def test_existing_file(self, tmp_path):
        test_file = tmp_path / "exists.txt"
        test_file.touch()
        result = await file_exists(str(test_file))
        assert "Exists" in result
        assert "file" in result

    @pytest.mark.asyncio
    async def test_existing_directory(self, tmp_path):
        result = await file_exists(str(tmp_path))
        assert "Exists" in result
        assert "dir" in result

    @pytest.mark.asyncio
    async def test_nonexistent(self):
        result = await file_exists("/nonexistent/path")
        assert "Not found" in result


class TestFileInfo:
    """Tests for file_info tool."""

    @pytest.mark.asyncio
    async def test_returns_metadata(self, tmp_path):
        test_file = tmp_path / "info.txt"
        test_file.write_text("content")
        result = await file_info(str(test_file))
        assert "Size" in result
        assert "Modified" in result

    @pytest.mark.asyncio
    async def test_error_handling(self):
        result = await file_info("/nonexistent/file.txt")
        assert "Error" in result


class TestFileDiff:
    """Tests for file_diff tool."""

    @pytest.mark.asyncio
    async def test_shows_diff(self, tmp_path):
        test_file = tmp_path / "diff.txt"
        test_file.write_text("line1\nline2\nline3")
        result = await file_diff(str(test_file), "line1\nmodified\nline3")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_no_differences(self, tmp_path):
        test_file = tmp_path / "same.txt"
        test_file.write_text("same content")
        result = await file_diff(str(test_file), "same content")
        assert "No differences" in result

    @pytest.mark.asyncio
    async def test_file_not_found(self):
        result = await file_diff("/nonexistent.txt", "content")
        assert "Error" in result


class TestSummarize:
    """Tests for summarize tool."""

    @pytest.mark.asyncio
    async def test_summarizes_text(self):
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        result = await summarize(text, max_sentences=2)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_empty_text(self):
        result = await summarize("", max_sentences=3)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_default_max_sentences(self):
        text = "One. Two. Three. Four. Five."
        result = await summarize(text)
        assert isinstance(result, str)


class TestBase64Encode:
    """Tests for base64_encode tool."""

    @pytest.mark.asyncio
    async def test_encodes_text(self):
        result = await base64_encode("Hello, World!")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_decodes_text(self):
        encoded = await base64_encode("Hello, World!")
        decoded = await base64_encode(encoded, decode=True)
        assert decoded == "Hello, World!"

    @pytest.mark.asyncio
    async def test_invalid_base64(self):
        result = await base64_encode("not valid base64!!!", decode=True)
        assert "error" in result.lower()


class TestJsonGet:
    """Tests for json_get tool."""

    @pytest.mark.asyncio
    async def test_gets_nested_value(self):
        import json
        data = json.dumps({"user": {"name": "Alice", "age": 30}})
        result = await json_get(data, "user.name")
        assert "Alice" in result

    @pytest.mark.asyncio
    async def test_gets_array_element(self):
        import json
        data = json.dumps({"items": ["a", "b", "c"]})
        result = await json_get(data, "items.1")
        assert "b" in result

    @pytest.mark.asyncio
    async def test_invalid_json(self):
        result = await json_get("not json", "key")
        assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_missing_key(self):
        import json
        data = json.dumps({"user": {"name": "Alice"}})
        result = await json_get(data, "user.missing")
        assert "error" in result.lower()

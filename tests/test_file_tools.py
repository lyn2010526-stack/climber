"""Tests for file handling tools."""

from pathlib import Path

import pytest

from app.tools.file_tools import FileTools


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def file_tools(tmp_workspace: Path) -> FileTools:
    return FileTools(tmp_workspace)


class TestFileRead:
    """Tests for file reading operations."""

    def test_read_existing_file(self, file_tools):
        file_tools.write_file("test.txt", "Hello World")
        result = file_tools.read_file("test.txt")
        assert "error" not in result
        assert result["content"] == "Hello World"

    def test_read_nonexistent_file(self, file_tools):
        result = file_tools.read_file("nonexistent.txt")
        assert "error" in result

    def test_read_directory_fails(self, file_tools):
        file_tools.workspace.mkdir(exist_ok=True)
        result = file_tools.read_file(".")
        assert "error" in result

    def test_read_with_offset(self, file_tools):
        file_tools.write_file("lines.txt", "line1\nline2\nline3")
        result = file_tools.read_file("lines.txt", offset=1)
        assert "line1" not in result["content"]

    def test_read_with_limit(self, file_tools):
        file_tools.write_file("lines.txt", "line1\nline2\nline3")
        result = file_tools.read_file("lines.txt", limit=2)
        assert len(result["content"].split("\n")) == 2

    def test_read_with_encoding(self, file_tools):
        file_tools.write_file("encoded.txt", "hello")
        result = file_tools.read_file("encoded.txt", encoding="utf-8")
        assert result["encoding"] == "utf-8"

    def test_path_traversal_blocked(self, file_tools):
        with pytest.raises(ValueError, match="traversal"):
            file_tools.read_file("../../etc/passwd")


class TestFileWrite:
    """Tests for file writing operations."""

    def test_write_new_file(self, file_tools):
        result = file_tools.write_file("new.txt", "content")
        assert result["size"] > 0
        assert result["lines"] == 1

    def test_write_nested_path(self, file_tools):
        file_tools.write_file("a/b/c.txt", "nested")
        assert (file_tools.workspace / "a/b/c.txt").exists()

    def test_write_append(self, file_tools):
        file_tools.write_file("append.txt", "first")
        file_tools.write_file("append.txt", "second", append=True)
        result = file_tools.read_file("append.txt")
        assert "first" in result["content"]
        assert "second" in result["content"]

    def test_write_overwrite(self, file_tools):
        file_tools.write_file("overwrite.txt", "old")
        file_tools.write_file("overwrite.txt", "new")
        result = file_tools.read_file("overwrite.txt")
        assert result["content"] == "new"

    def test_write_multiline(self, file_tools):
        result = file_tools.write_file("multi.txt", "a\nb\nc")
        assert result["lines"] == 3


class TestFileList:
    """Tests for directory listing."""

    def test_list_empty_directory(self, file_tools):
        result = file_tools.list_files(".")
        assert result["total"] == 0

    def test_list_with_files(self, file_tools):
        file_tools.write_file("a.txt", "a")
        file_tools.write_file("b.txt", "b")
        result = file_tools.list_files(".")
        assert result["total"] == 2

    def test_list_with_pattern(self, file_tools):
        file_tools.write_file("test.txt", "t")
        file_tools.write_file("test.py", "p")
        result = file_tools.list_files(".", pattern="*.txt")
        assert result["total"] == 1

    def test_list_recursive(self, file_tools):
        file_tools.write_file("sub/deep.txt", "deep")
        result = file_tools.list_files(".", recursive=True)
        paths = [item["path"] for item in result["items"]]
        assert any("deep.txt" in p for p in paths)

    def test_list_excludes_hidden(self, file_tools):
        file_tools.write_file(".hidden", "hidden")
        file_tools.write_file("visible.txt", "visible")
        result = file_tools.list_files(".")
        names = [item["name"] for item in result["items"]]
        assert ".hidden" not in names

    def test_list_includes_hidden_when_requested(self, file_tools):
        file_tools.write_file(".hidden", "hidden")
        result = file_tools.list_files(".", include_hidden=True)
        names = [item["name"] for item in result["items"]]
        assert ".hidden" in names


class TestFileOperations:
    """Tests for file copy, move, delete operations."""

    def test_copy_file(self, file_tools):
        file_tools.write_file("src.txt", "data")
        result = file_tools.copy_file("src.txt", "dst.txt")
        assert result["copied"] is True
        assert (file_tools.workspace / "dst.txt").exists()

    def test_copy_overwrite_protection(self, file_tools):
        file_tools.write_file("src.txt", "a")
        file_tools.write_file("dst.txt", "b")
        result = file_tools.copy_file("src.txt", "dst.txt", overwrite=False)
        assert "error" in result

    def test_copy_with_overwrite(self, file_tools):
        file_tools.write_file("src.txt", "a")
        file_tools.write_file("dst.txt", "b")
        file_tools.copy_file("src.txt", "dst.txt", overwrite=True)
        result = file_tools.read_file("dst.txt")
        assert result["content"] == "a"

    def test_move_file(self, file_tools):
        file_tools.write_file("from.txt", "data")
        file_tools.move_file("from.txt", "to.txt")
        assert not (file_tools.workspace / "from.txt").exists()
        assert (file_tools.workspace / "to.txt").exists()

    def test_delete_file(self, file_tools):
        file_tools.write_file("delete_me.txt", "bye")
        result = file_tools.delete_file("delete_me.txt")
        assert result["deleted"] is True
        assert not (file_tools.workspace / "delete_me.txt").exists()

    def test_delete_directory_recursive(self, file_tools):
        file_tools.write_file("sub/file.txt", "data")
        result = file_tools.delete_file("sub", recursive=True)
        assert result["deleted"] is True

    def test_delete_nonexistent(self, file_tools):
        result = file_tools.delete_file("nonexistent.txt")
        assert "error" in result


class TestFileInfo:
    """Tests for file metadata."""

    def test_info_existing_file(self, file_tools):
        file_tools.write_file("info.txt", "data")
        result = file_tools.file_info("info.txt")
        assert result["name"] == "info.txt"
        assert result["type"] == "file"
        assert "checksum_sha256" in result

    def test_info_directory(self, file_tools):
        result = file_tools.file_info(".")
        assert result["type"] == "directory"

    def test_info_nonexistent(self, file_tools):
        result = file_tools.file_info("nonexistent")
        assert "error" in result

    def test_info_includes_mime_type(self, file_tools):
        file_tools.write_file("doc.txt", "text")
        result = file_tools.file_info("doc.txt")
        assert "mime_type" in result


class TestFileSearch:
    """Tests for file content search."""

    def test_search_found(self, file_tools):
        file_tools.write_file("a.txt", "hello world")
        result = file_tools.search_files("hello", ".", "*.txt")
        assert result["total"] > 0

    def test_search_not_found(self, file_tools):
        file_tools.write_file("a.txt", "hello world")
        result = file_tools.search_files("nonexistent", ".", "*.txt")
        assert result["total"] == 0

    def test_search_regex(self, file_tools):
        file_tools.write_file("log.txt", "error: something failed\ninfo: ok")
        result = file_tools.search_files(r"^error:", ".", "*.txt")
        assert result["total"] == 1

    def test_search_with_max_results(self, file_tools):
        for i in range(10):
            file_tools.write_file(f"f{i}.txt", f"match {i}")
        result = file_tools.search_files("match", ".", "*.txt", max_results=5)
        assert result["total"] == 5


class TestFileArchive:
    """Tests for archive operations."""

    def test_create_archive(self, file_tools):
        file_tools.write_file("a.txt", "data a")
        file_tools.write_file("b.txt", "data b")
        result = file_tools.archive_file("create", "test.zip", ["a.txt", "b.txt"])
        assert result["operation"] == "create"
        assert (file_tools.workspace / "test.zip").exists()

    def test_extract_archive(self, file_tools):
        file_tools.write_file("archived.txt", "archived content")
        file_tools.archive_file("create", "test.zip", ["archived.txt"])
        result = file_tools.archive_file("extract", "test.zip", destination="extracted")
        assert result["operation"] == "extract"
        assert (file_tools.workspace / "extracted").exists()

    def test_unknown_operation(self, file_tools):
        result = file_tools.archive_file("unknown", "test.zip")
        assert "error" in result

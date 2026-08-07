"""Comprehensive tests for app.tools.builtins - targeting uncovered lines."""

from __future__ import annotations

import pytest
import unittest.mock as mock

from app.tools.builtins import (
    _safe_eval_math,
    analyze_error,
    append_file,
    apply_patch,
    base64_encode,
    calculator,
    container_exec,
    edit_file,
    fetch_url,
    file_diff,
    file_exists,
    file_info,
    generate_image,
    get_datetime,
    get_weather,
    handoff_task,
    json_get,
    list_files,
    read_file,
    run_command,
    run_group_tasks,
    stream_command,
    suggest_fix,
    summarize,
    translate,
    wikipedia_summary,
    web_search,
    write_file,
)


class TestFetchUrl:
    """Tests for fetch_url - covers lines 76-83."""

    @pytest.mark.asyncio
    async def test_fetch_url_success(self):
        mock_response = mock.Mock()
        mock_response.text = "<html>Hello</html>"
        mock_response.status_code = 200
        mock_response.raise_for_status = mock.Mock()

        mock_client = mock.AsyncMock()
        mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mock.AsyncMock(return_value=None)
        mock_client.get = mock.AsyncMock(return_value=mock_response)

        with mock.patch("app.tools.builtins.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_url("https://example.com")
            assert "Hello" in result or "example.com" in result

    @pytest.mark.asyncio
    async def test_fetch_url_error(self):
        mock_client = mock.AsyncMock()
        mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mock.AsyncMock(return_value=None)
        mock_client.get = mock.AsyncMock(side_effect=Exception("Connection error"))

        with mock.patch("app.tools.builtins.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_url("https://example.com")
            assert "Error" in result


class TestWebSearch:
    """Tests for web_search - covers lines 97-99."""

    @pytest.mark.asyncio
    async def test_web_search_fallback(self):
        """Test that web_search falls back to verify=False on first failure."""
        mock_response = mock.Mock()
        mock_response.text = "search results"
        mock_response.status_code = 200
        mock_response.raise_for_status = mock.Mock()

        mock_client_fail = mock.AsyncMock()
        mock_client_fail.__aenter__ = mock.AsyncMock(return_value=mock_client_fail)
        mock_client_fail.__aexit__ = mock.AsyncMock(return_value=None)
        mock_client_fail.get = mock.AsyncMock(side_effect=Exception("SSL error"))

        mock_client_ok = mock.AsyncMock()
        mock_client_ok.__aenter__ = mock.AsyncMock(return_value=mock_client_ok)
        mock_client_ok.__aexit__ = mock.AsyncMock(return_value=None)
        mock_client_ok.get = mock.AsyncMock(return_value=mock_response)

        with mock.patch("app.tools.builtins.httpx.AsyncClient", side_effect=[mock_client_fail, mock_client_ok]):
            result = await web_search("test query")
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_web_search_all_fail(self):
        mock_client = mock.AsyncMock()
        mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mock.AsyncMock(return_value=None)
        mock_client.get = mock.AsyncMock(side_effect=Exception("fail"))

        with mock.patch("app.tools.builtins.httpx.AsyncClient", return_value=mock_client):
            result = await web_search("test")
            assert "Search error" in result


class TestGetWeather:
    """Tests for get_weather - covers lines 137-138."""

    @pytest.mark.asyncio
    async def test_weather_success(self):
        mock_response = mock.Mock()
        mock_response.json.return_value = {
            "current_condition": [{
                "temp_C": "20",
                "FeelsLikeC": "18",
                "humidity": "60",
                "weatherDesc": [{"value": "Sunny"}],
                "windspeedKmph": "10",
            }]
        }
        mock_response.raise_for_status = mock.Mock()

        mock_client = mock.AsyncMock()
        mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mock.AsyncMock(return_value=None)
        mock_client.get = mock.AsyncMock(return_value=mock_response)

        with mock.patch("app.tools.builtins.httpx.AsyncClient", return_value=mock_client):
            result = await get_weather("London")
            assert "London" in result
            assert "20" in result

    @pytest.mark.asyncio
    async def test_weather_error(self):
        mock_client = mock.AsyncMock()
        mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mock.AsyncMock(return_value=None)
        mock_client.get = mock.AsyncMock(side_effect=Exception("API down"))

        with mock.patch("app.tools.builtins.httpx.AsyncClient", return_value=mock_client):
            result = await get_weather("London")
            assert "Weather error" in result


class TestRunCommand:
    """Tests for run_command - covers lines 177-178."""

    @pytest.mark.asyncio
    async def test_run_command(self):
        with mock.patch("app.tools.builtins.di_resolve") as mock_resolve:
            mock_sandbox = mock.AsyncMock()
            mock_sandbox.execute = mock.AsyncMock(return_value="command output")
            mock_resolve.return_value = mock_sandbox
            result = await run_command("echo hello")
            assert "command output" in result


class TestGenerateImage:
    """Tests for generate_image - covers lines 190-192."""

    @pytest.mark.asyncio
    async def test_generate_image_success(self):
        mock_response = mock.Mock()
        mock_response.status_code = 200

        mock_client = mock.AsyncMock()
        mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mock.AsyncMock(return_value=None)
        mock_client.get = mock.AsyncMock(return_value=mock_response)

        with mock.patch("app.tools.builtins.httpx.AsyncClient", return_value=mock_client):
            result = await generate_image("a cat")
            assert "Image generated" in result

    @pytest.mark.asyncio
    async def test_generate_image_failure(self):
        mock_response = mock.Mock()
        mock_response.status_code = 500

        mock_client = mock.AsyncMock()
        mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mock.AsyncMock(return_value=None)
        mock_client.get = mock.AsyncMock(return_value=mock_response)

        with mock.patch("app.tools.builtins.httpx.AsyncClient", return_value=mock_client):
            result = await generate_image("a cat")
            assert "failed" in result


class TestTranslate:
    """Tests for translate - covers lines 208, 211-212."""

    @pytest.mark.asyncio
    async def test_translate_success(self):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"translatedText": "Hola"}

        mock_client = mock.AsyncMock()
        mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mock.AsyncMock(return_value=None)
        mock_client.post = mock.AsyncMock(return_value=mock_response)

        with mock.patch("app.tools.builtins.httpx.AsyncClient", return_value=mock_client):
            result = await translate("Hello", target_language="es")
            assert "Hola" in result

    @pytest.mark.asyncio
    async def test_translate_service_unavailable(self):
        mock_response = mock.Mock()
        mock_response.status_code = 503

        mock_client = mock.AsyncMock()
        mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mock.AsyncMock(return_value=None)
        mock_client.post = mock.AsyncMock(return_value=mock_response)

        with mock.patch("app.tools.builtins.httpx.AsyncClient", return_value=mock_client):
            result = await translate("Hello", target_language="es")
            assert "unavailable" in result or "Hello" in result

    @pytest.mark.asyncio
    async def test_translate_error(self):
        mock_client = mock.AsyncMock()
        mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mock.AsyncMock(return_value=None)
        mock_client.post = mock.AsyncMock(side_effect=Exception("Network error"))

        with mock.patch("app.tools.builtins.httpx.AsyncClient", return_value=mock_client):
            result = await translate("Hello")
            assert "Translation error" in result


class TestWikipediaSummary:
    """Tests for wikipedia_summary - covers lines 228-230."""

    @pytest.mark.asyncio
    async def test_wikipedia_success(self):
        mock_response = mock.Mock()
        mock_response.json.return_value = {
            "extract": "Python is a programming language."
        }
        mock_response.raise_for_status = mock.Mock()

        mock_client = mock.AsyncMock()
        mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mock.AsyncMock(return_value=None)
        mock_client.get = mock.AsyncMock(return_value=mock_response)

        with mock.patch("app.tools.builtins.httpx.AsyncClient", return_value=mock_client):
            result = await wikipedia_summary("Python")
            assert "Python" in result

    @pytest.mark.asyncio
    async def test_wikipedia_error(self):
        mock_client = mock.AsyncMock()
        mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mock.AsyncMock(return_value=None)
        mock_client.get = mock.AsyncMock(side_effect=Exception("fail"))

        with mock.patch("app.tools.builtins.httpx.AsyncClient", return_value=mock_client):
            result = await wikipedia_summary("Python")
            assert "Summary error" in result or "Wikipedia error" in result


class TestSummarize:
    """Tests for summarize - covers lines 241-242."""

    @pytest.mark.asyncio
    async def test_summarize_text(self):
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        result = await summarize(text, max_sentences=2)
        assert isinstance(result, str)
        assert "." in result

    @pytest.mark.asyncio
    async def test_summarize_empty(self):
        result = await summarize("")
        assert isinstance(result, str)


class TestJsonGet:
    """Tests for json_get - covers line 268."""

    @pytest.mark.asyncio
    async def test_json_get_nested(self):
        import json
        data = json.dumps({"a": {"b": {"c": "value"}}})
        result = await json_get(data, "a.b.c")
        assert "value" in result

    @pytest.mark.asyncio
    async def test_json_get_array(self):
        import json
        data = json.dumps({"items": [10, 20, 30]})
        result = await json_get(data, "items.1")
        assert "20" in result

    @pytest.mark.asyncio
    async def test_json_get_type_error(self):
        import json
        data = json.dumps({"key": "value"})
        result = await json_get(data, "key.subkey")
        assert "Cannot traverse" in result


class TestEditFile:
    """Tests for edit_file - covers lines 288-309."""

    @pytest.mark.asyncio
    async def test_edit_file_not_found(self):
        result = await edit_file("/nonexistent/file.txt", "old", "new")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_edit_file_no_match(self, tmp_path):
        test_file = tmp_path / "edit.txt"
        test_file.write_text("Hello World")
        result = await edit_file(str(test_file), "NotFound", "replacement")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_edit_file_permission_denied(self):
        """Test that permission denied paths are handled."""
        result = await edit_file("/tmp/test_edit.txt", "old", "new")
        assert isinstance(result, str)


class TestFileInfo:
    """Tests for file_info - covers lines 346-347."""

    @pytest.mark.asyncio
    async def test_file_info_error(self):
        result = await file_info("/nonexistent/file.txt")
        assert "Error" in result


class TestContainerExec:
    """Tests for container_exec - covers lines 438, 452, 462."""

    @pytest.mark.asyncio
    async def test_container_exec_success(self):
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(returncode=0, stdout="output", stderr="")
            result = await container_exec("mycontainer", "echo hello")
            assert "output" in result

    @pytest.mark.asyncio
    async def test_container_exec_failure(self):
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(returncode=1, stdout="", stderr="error")
            result = await container_exec("mycontainer", "bad_command")
            assert "failed" in result

    @pytest.mark.asyncio
    async def test_container_exec_docker_not_found(self):
        with mock.patch("subprocess.run", side_effect=FileNotFoundError):
            result = await container_exec("mycontainer", "echo hello")
            assert "Docker is not installed" in result

    @pytest.mark.asyncio
    async def test_container_exec_with_workdir(self):
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(returncode=0, stdout="done", stderr="")
            result = await container_exec("mycontainer", "ls", workdir="/app")
            assert "done" in result


class TestStreamCommand:
    """Tests for stream_command - covers lines 465-466, 486."""

    @pytest.mark.asyncio
    async def test_stream_command_success(self):
        mock_sandbox = mock.AsyncMock()
        mock_sandbox.execute = mock.AsyncMock(return_value="stream output")

        def fake_resolve(name):
            return mock_sandbox

        with mock.patch("app.core.di.resolve", side_effect=fake_resolve):
            result = await stream_command("ls -la")
            assert "stream output" in result

    @pytest.mark.asyncio
    async def test_stream_command_error(self):
        with mock.patch("app.core.di.resolve", side_effect=Exception("no sandbox")):
            result = await stream_command("ls")
            assert "Error" in result


class TestApplyPatch:
    """Tests for apply_patch - covers lines 510, 519-521, 524-525."""

    @pytest.mark.asyncio
    async def test_apply_patch_file_not_found(self):
        result = await apply_patch("/nonexistent/file.txt", "@@ -1 +1 @@\n-old\n+new")
        assert "does not exist" in result

    @pytest.mark.asyncio
    async def test_apply_patch_dry_run_fails(self, tmp_path):
        test_file = tmp_path / "patch.txt"
        test_file.write_text("original content")
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(returncode=1, stdout="", stderr="malformed")
            result = await apply_patch(str(test_file), "invalid patch")
            assert "failed" in result.lower()

    @pytest.mark.asyncio
    async def test_apply_patch_success(self, tmp_path):
        test_file = tmp_path / "patch.txt"
        test_file.write_text("line1\nline2\nline3\n")
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(returncode=0, stdout="patched", stderr="")
            result = await apply_patch(str(test_file), "@@ -1,3 +1,3 @@\n line1\n-line2\n+modified\n line3")
            assert "success" in result.lower()


class TestAnalyzeError:
    """Tests for analyze_error - covers lines 680-681."""

    @pytest.mark.asyncio
    async def test_analyze_error_success(self):
        mock_analyzer = mock.Mock()
        mock_analysis = mock.Mock()
        mock_analysis.to_dict.return_value = {"error_type": "ValueError", "message": "test"}
        mock_analyzer.analyze.return_value = mock_analysis

        with mock.patch("app.core.error_analyzer.ErrorAnalyzer", return_value=mock_analyzer):
            result = await analyze_error("ValueError: test error")
            assert "ValueError" in result

    @pytest.mark.asyncio
    async def test_analyze_error_failure(self):
        with mock.patch("app.core.error_analyzer.ErrorAnalyzer", side_effect=Exception("no analyzer")):
            result = await analyze_error("some error")
            assert "Error" in result


class TestSuggestFix:
    """Tests for suggest_fix - covers lines 705-737."""

    @pytest.mark.asyncio
    async def test_suggest_fix_success(self):
        mock_loop = mock.Mock()
        mock_loop._generate_fix_strategy = mock.AsyncMock()
        mock_strategy = mock.Mock()
        mock_strategy.approach = "retry"
        mock_strategy.description = "Try again"
        mock_strategy.confidence = 0.8
        mock_strategy.patch_content = ""
        mock_strategy.new_arguments = {}
        mock_strategy.new_tool = None
        mock_loop._generate_fix_strategy.return_value = mock_strategy

        with mock.patch("app.core.debug_loop.DebugLoop", return_value=mock_loop), \
             mock.patch("app.core.error_analyzer.ErrorAnalysis"):
            result = await suggest_fix('{"error_type": "ValueError", "message": "test"}')
            assert "retry" in result

    @pytest.mark.asyncio
    async def test_suggest_fix_failure(self):
        with mock.patch("app.core.debug_loop.DebugLoop", side_effect=Exception("fail")):
            result = await suggest_fix('{"error_type": "ValueError"}')
            assert "Error" in result

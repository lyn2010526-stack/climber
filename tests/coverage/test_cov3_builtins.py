"""Coverage tests for app.tools.builtins (network + fs mocked)."""

from __future__ import annotations

import json
import subprocess

import pytest

from app.tools import builtins

# ─── fakes ──────────────────────────────────────────────────────────────────


class FakeResponse:
    def __init__(
        self,
        *,
        text="",
        content=b"",
        status_code=200,
        json_data=None,
        has_redirect_location=False,
        url="http://example.com/a",
        headers=None,
    ):
        self.text = text
        self.content = content
        self.status_code = status_code
        self._json = json_data
        self.has_redirect_location = has_redirect_location
        self.url = url
        self.headers = headers or {}
        self.raised = False

    def raise_for_status(self):
        self.raised = True

    def json(self):
        return self._json


class FakeHTTPClient:
    def __init__(self, *args, responses=None, error=None, **kwargs):
        self._responses = list(responses or [])
        self._error = error
        self.get_calls = []
        self.post_calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def _next(self):
        if self._error:
            raise self._error
        if self._responses:
            return self._responses.pop(0)
        return FakeResponse()

    async def get(self, url, **kwargs):
        self.get_calls.append(url)
        return self._next()

    async def post(self, url, **kwargs):
        self.post_calls.append(url)
        return self._next()


@pytest.fixture
def patch_httpx(monkeypatch):
    import httpx

    def _install(client):
        monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: client)
        return client

    return _install


@pytest.fixture
def allow_outbound(monkeypatch):
    monkeypatch.setattr(builtins, "_outbound_denial", lambda url: "")


# ─── _outbound_denial / helpers ─────────────────────────────────────────────


def test_outbound_denial_ssrf_blocked(monkeypatch):
    monkeypatch.setattr(builtins, "blocked_reason", lambda url: "loopback")
    assert builtins._outbound_denial("http://127.0.0.1") == "loopback"


def test_outbound_denial_allowlist_blocked(monkeypatch):
    monkeypatch.setattr(builtins, "blocked_reason", lambda url: "")
    monkeypatch.setattr(
        builtins,
        "network_allowlist",
        type("NA", (), {"check_url": lambda self, url: (False, "no")})(),
    )
    assert builtins._outbound_denial("http://x") == "blocked by network allowlist: no"


def test_outbound_denial_allowed(monkeypatch):
    monkeypatch.setattr(builtins, "blocked_reason", lambda url: "")
    monkeypatch.setattr(
        builtins, "network_allowlist", type("NA", (), {"check_url": lambda self, url: (True, "")})()
    )
    assert builtins._outbound_denial("http://x") == ""


def test_safe_eval_math_rejects_unsafe_node():
    with pytest.raises(ValueError, match="Unsafe math expression node"):
        builtins._safe_eval_math("1 if True else 2", {})


def test_safe_eval_math_allows_locals():
    assert builtins._safe_eval_math("x + 1", {"x": 41}) == 42


# ─── simple tools ───────────────────────────────────────────────────────────


async def test_get_datetime():
    out = await builtins.get_datetime()
    assert "T" in out


async def test_calculator_basic():
    assert await builtins.calculator("2 + 2") == "4"
    assert await builtins.calculator("2 ^ 3") == "8"


async def test_calculator_rejects_illegal_chars():
    out = await builtins.calculator("2+2\nimport os")
    assert out == "Error: Only math operators and functions allowed"


async def test_calculator_rejects_unsupported_name():
    out = await builtins.calculator("foo(1)")
    assert "Unsupported name" in out


async def test_summarize_keeps_long_sentences():
    text = "This is the first sentence. This is the second sentence. Short."
    out = await builtins.summarize(text, max_sentences=1)
    assert out.endswith(".")
    assert "first sentence" in out


async def test_summarize_no_sentences():
    assert await builtins.summarize("a. b.") == "."


async def test_summarize_error():
    out = await builtins.summarize(123)  # type: ignore[arg-type]
    assert out.startswith("Summary error:")


async def test_base64_roundtrip():
    encoded = await builtins.base64_encode("hello")
    assert encoded == "aGVsbG8="
    assert await builtins.base64_encode(encoded, decode=True) == "hello"


async def test_base64_decode_error():
    out = await builtins.base64_encode("!!!not-base64!!!", decode=True)
    assert out.startswith("Base64 error:")


async def test_json_get_dict_and_list():
    data = json.dumps({"user": {"name": "ada"}, "items": [1, 2, 3]})
    assert json.loads(await builtins.json_get(data, "user.name")) == "ada"
    assert json.loads(await builtins.json_get(data, "items.1")) == 2


async def test_json_get_cannot_traverse():
    out = await builtins.json_get('{"a": 1}', "a.b")
    assert out.startswith("Error: Cannot traverse into")


async def test_json_get_parse_error():
    out = await builtins.json_get("{not json", "a")
    assert out.startswith("JSON parse error:")


# ─── fetch_url ──────────────────────────────────────────────────────────────


async def test_fetch_url_blocked(monkeypatch):
    monkeypatch.setattr(builtins, "_outbound_denial", lambda url: "ssrf")
    assert await builtins.fetch_url("http://x") == "Error fetching URL: ssrf"


async def test_fetch_url_success(patch_httpx, allow_outbound):
    client = patch_httpx(FakeHTTPClient(responses=[FakeResponse(text="body", status_code=200)]))
    out = await builtins.fetch_url("http://example.com/a")
    assert out == "URL: http://example.com/a\nStatus: 200\n\nbody"
    assert client.get_calls == ["http://example.com/a"]


async def test_fetch_url_redirect_allowed(patch_httpx, allow_outbound):
    responses = [
        FakeResponse(has_redirect_location=True, headers={"location": "/b"}),
        FakeResponse(text="final", status_code=200),
    ]
    client = patch_httpx(FakeHTTPClient(responses=responses))
    out = await builtins.fetch_url("http://example.com/a")
    assert "final" in out
    assert client.get_calls == ["http://example.com/a", "http://example.com/b"]


async def test_fetch_url_too_many_redirects(patch_httpx, allow_outbound):
    responses = [
        FakeResponse(has_redirect_location=True, headers={"location": "/loop"}) for _ in range(6)
    ]
    patch_httpx(FakeHTTPClient(responses=responses))
    out = await builtins.fetch_url("http://example.com/a")
    assert out == "Error fetching URL: too many redirects (maximum 5)"


async def test_fetch_url_redirect_blocked(patch_httpx, monkeypatch):
    calls = {"n": 0}

    def _deny(url):
        calls["n"] += 1
        return "" if calls["n"] == 1 else "blocked redirect target"

    monkeypatch.setattr(builtins, "_outbound_denial", _deny)
    patch_httpx(
        FakeHTTPClient(
            responses=[FakeResponse(has_redirect_location=True, headers={"location": "/evil"})]
        )
    )
    out = await builtins.fetch_url("http://example.com/a")
    assert out == "Error fetching URL: redirect blocked: blocked redirect target"


async def test_fetch_url_timeout(patch_httpx, allow_outbound):
    import httpx

    patch_httpx(FakeHTTPClient(error=httpx.TimeoutException("slow")))
    out = await builtins.fetch_url("http://example.com/a")
    assert out == "Error fetching URL: request timed out (15s timeout)"


async def test_fetch_url_error(patch_httpx, allow_outbound):
    patch_httpx(FakeHTTPClient(error=RuntimeError("boom")))
    out = await builtins.fetch_url("http://example.com/a")
    assert out == "Error fetching URL: boom"


# ─── web_search ─────────────────────────────────────────────────────────────


async def test_web_search_blocked(monkeypatch):
    monkeypatch.setattr(builtins, "_outbound_denial", lambda url: "no")
    assert await builtins.web_search("q") == "Search error: no"


async def test_web_search_success(patch_httpx, allow_outbound):
    patch_httpx(FakeHTTPClient(responses=[FakeResponse(text="<b>Hello</b>   world")]))
    out = await builtins.web_search("python")
    assert out.startswith("Search results for: python\n\n")
    assert "<b>" not in out
    assert "Hello" in out


async def test_web_search_error(patch_httpx, allow_outbound):
    patch_httpx(FakeHTTPClient(error=RuntimeError("down")))
    out = await builtins.web_search("q")
    assert out == "Search error: down"


# ─── get_weather ────────────────────────────────────────────────────────────


async def test_get_weather_blocked(monkeypatch):
    monkeypatch.setattr(builtins, "_outbound_denial", lambda url: "no")
    assert await builtins.get_weather("Paris") == "Weather error: no"


async def test_get_weather_success(patch_httpx, allow_outbound):
    data = {
        "current_condition": [
            {
                "temp_C": "18",
                "FeelsLikeC": "17",
                "humidity": "60",
                "weatherDesc": [{"value": "Cloudy"}],
                "windspeedKmph": "12",
            }
        ]
    }
    patch_httpx(FakeHTTPClient(responses=[FakeResponse(json_data=data)]))
    out = await builtins.get_weather("Paris")
    assert "Temperature: 18" in out
    assert "Cloudy" in out


async def test_get_weather_error(patch_httpx, allow_outbound):
    patch_httpx(FakeHTTPClient(error=RuntimeError("boom")))
    assert (await builtins.get_weather("Paris")).startswith("Weather error:")


# ─── file tools ─────────────────────────────────────────────────────────────


async def test_read_file_invalid_path():
    out = await builtins.read_file("/etc/passwd")
    assert out.startswith("Error reading file:")


async def test_read_file_success(tmp_path):
    target = tmp_path / "f.txt"
    target.write_text("data", encoding="utf-8")
    assert await builtins.read_file(str(target)) == "data"


async def test_read_file_exception(tmp_path):
    assert (await builtins.read_file(str(tmp_path))).startswith("Error reading file:")


async def test_write_file_invalid_path():
    out = await builtins.write_file("/etc/x", "y")
    assert out.startswith("Error writing file:")


async def test_write_file_success(tmp_path):
    target = tmp_path / "out.txt"
    assert await builtins.write_file(str(target), "hi") == f"File written: {target}"
    assert target.read_text(encoding="utf-8") == "hi"


async def test_write_file_exception(tmp_path, monkeypatch):
    def _boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("builtins.open", _boom)
    out = await builtins.write_file(str(tmp_path / "out.txt"), "hi")
    assert out.startswith("Error writing file:")


async def test_list_files_success(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    out = await builtins.list_files(str(tmp_path))
    assert "[dir] sub" in out
    assert "[file] a.txt" in out


async def test_list_files_empty(tmp_path):
    assert await builtins.list_files(str(tmp_path)) == "Directory is empty"


async def test_list_files_error():
    assert (await builtins.list_files("/nonexistent-cov3")).startswith("Error listing directory:")


async def test_run_command(monkeypatch):
    class _Sandbox:
        async def execute(self, command):
            return f"ran:{command}"

    monkeypatch.setattr(builtins, "di_resolve", lambda name: _Sandbox())
    assert await builtins.run_command("ls") == "ran:ls"


# ─── image / translation / wikipedia ────────────────────────────────────────


async def test_generate_image_blocked(monkeypatch):
    monkeypatch.setattr(builtins, "_outbound_denial", lambda url: "no")
    assert (await builtins.generate_image("cat")).startswith("Image generation error: no")


async def test_generate_image_success(patch_httpx, allow_outbound):
    patch_httpx(FakeHTTPClient(responses=[FakeResponse(status_code=200)]))
    assert (await builtins.generate_image("cat")).startswith("Image generated: http")


async def test_generate_image_http_error(patch_httpx, allow_outbound):
    patch_httpx(FakeHTTPClient(responses=[FakeResponse(status_code=500)]))
    assert await builtins.generate_image("cat") == "Image generation failed: HTTP 500"


async def test_generate_image_exception(patch_httpx, allow_outbound):
    patch_httpx(FakeHTTPClient(error=RuntimeError("boom")))
    assert (await builtins.generate_image("cat")).startswith("Image generation error:")


async def test_translate_blocked(monkeypatch):
    monkeypatch.setattr(builtins, "_outbound_denial", lambda url: "no")
    assert (await builtins.translate("hi")).startswith("Translation error: no")


async def test_translate_success(patch_httpx, allow_outbound):
    patch_httpx(FakeHTTPClient(responses=[FakeResponse(json_data={"translatedText": "hola"})]))
    assert await builtins.translate("hi", target_language="es") == "hola"


async def test_translate_unavailable(patch_httpx, allow_outbound):
    patch_httpx(FakeHTTPClient(responses=[FakeResponse(status_code=503)]))
    out = await builtins.translate("hi")
    assert out.startswith("Translation service unavailable. Text: hi")


async def test_translate_exception(patch_httpx, allow_outbound):
    patch_httpx(FakeHTTPClient(error=RuntimeError("boom")))
    assert (await builtins.translate("hi")).startswith("Translation error:")


async def test_wikipedia_blocked(monkeypatch):
    monkeypatch.setattr(builtins, "_outbound_denial", lambda url: "no")
    assert (await builtins.wikipedia_summary("x")).startswith("Wikipedia error: no")


async def test_wikipedia_success(patch_httpx, allow_outbound):
    data = {
        "title": "Ada",
        "extract": "Mathematician",
        "content_urls": {"desktop": {"page": "http://en.wikipedia.org/Ada"}},
    }
    patch_httpx(FakeHTTPClient(responses=[FakeResponse(json_data=data)]))
    out = await builtins.wikipedia_summary("Ada")
    assert "## Ada" in out
    assert "Mathematician" in out


async def test_wikipedia_not_found(patch_httpx, allow_outbound):
    patch_httpx(FakeHTTPClient(responses=[FakeResponse(status_code=404)]))
    assert await builtins.wikipedia_summary("Nope") == "Wikipedia: No article found for 'Nope'"


async def test_wikipedia_exception(patch_httpx, allow_outbound):
    patch_httpx(FakeHTTPClient(error=RuntimeError("boom")))
    assert (await builtins.wikipedia_summary("x")).startswith("Wikipedia error:")


# ─── edit_file ──────────────────────────────────────────────────────────────


@pytest.fixture
def patch_edit_deps(monkeypatch):
    import app.core.file_patch as fp_mod
    import app.core.security_sandbox as sb_mod

    class FakeFilePatch:
        @staticmethod
        def validate_edit(path, old, new):
            return True, "ok"

        @staticmethod
        def preview_edit(path, old, new):
            return "DIFF", "ok"

    monkeypatch.setattr(fp_mod, "FilePatchService", FakeFilePatch)
    monkeypatch.setattr(fp_mod, "get_current_agent_mode", lambda: "default")
    monkeypatch.setattr(sb_mod, "security_sandbox", None)
    return fp_mod, sb_mod


async def test_edit_file_permission_denied(monkeypatch, tmp_path):
    import app.core.security_sandbox as sb_mod

    class DenySandbox:
        def validate_file_access(self, path, mode):
            return False, "no-perm"

    monkeypatch.setattr(sb_mod, "security_sandbox", DenySandbox())
    out = await builtins.edit_file(str(tmp_path / "f.txt"), "a", "b")
    assert out == "Permission denied: no-perm"


async def test_edit_file_validation_failed(monkeypatch, patch_edit_deps):
    fp_mod, _ = patch_edit_deps

    class BadPatch:
        @staticmethod
        def validate_edit(path, old, new):
            return False, "bad-edit"

    monkeypatch.setattr(fp_mod, "FilePatchService", BadPatch)
    out = await builtins.edit_file("/tmp/x", "a", "b")
    assert out == "Validation failed: bad-edit"


async def test_edit_file_preview_failed(monkeypatch, patch_edit_deps):
    fp_mod, _ = patch_edit_deps

    class NoPreview:
        @staticmethod
        def validate_edit(path, old, new):
            return True, "ok"

        @staticmethod
        def preview_edit(path, old, new):
            return "", "no-preview"

    monkeypatch.setattr(fp_mod, "FilePatchService", NoPreview)
    out = await builtins.edit_file("/tmp/x", "a", "b")
    assert out == "Preview failed: no-preview"


async def test_edit_file_plan_mode(monkeypatch, patch_edit_deps, tmp_path):
    fp_mod, _ = patch_edit_deps
    monkeypatch.setattr(fp_mod, "get_current_agent_mode", lambda: "plan")

    target = tmp_path / "f.txt"
    target.write_text("old content", encoding="utf-8")
    out = await builtins.edit_file(str(target), "old", "new")
    assert out.startswith("PLAN mode preview (no changes applied):")
    assert target.read_text(encoding="utf-8") == "old content"


async def test_edit_file_success(patch_edit_deps, tmp_path):
    target = tmp_path / "f.txt"
    target.write_text("hello world", encoding="utf-8")
    out = await builtins.edit_file(str(target), "world", "there")
    assert out.startswith(f"File updated: {target}")
    assert target.read_text(encoding="utf-8") == "hello there"


async def test_edit_file_allows_when_sandbox_permits(monkeypatch, patch_edit_deps, tmp_path):
    import app.core.security_sandbox as sb_mod

    class AllowSandbox:
        def validate_file_access(self, path, mode):
            return True, ""

    monkeypatch.setattr(sb_mod, "security_sandbox", AllowSandbox())
    target = tmp_path / "f.txt"
    target.write_text("hello world", encoding="utf-8")
    out = await builtins.edit_file(str(target), "world", "there")
    assert out.startswith(f"File updated: {target}")


async def test_edit_file_exception(monkeypatch, patch_edit_deps):
    fp_mod, _ = patch_edit_deps

    class Boom:
        @staticmethod
        def validate_edit(path, old, new):
            raise RuntimeError("boom")

    monkeypatch.setattr(fp_mod, "FilePatchService", Boom)
    out = await builtins.edit_file("/tmp/x", "a", "b")
    assert out.startswith("Error editing file:")


# ─── misc file tools ────────────────────────────────────────────────────────


async def test_file_diff_and_no_diff(tmp_path):
    target = tmp_path / "f.txt"
    target.write_text("line1\nline2", encoding="utf-8")
    out = await builtins.file_diff(str(target), "line1\nline3")
    assert "-line2" in out and "+line3" in out
    assert await builtins.file_diff(str(target), "line1\nline2") == "No differences"


async def test_file_diff_error():
    assert (await builtins.file_diff("/nonexistent-cov3", "x")).startswith("Error diffing file:")


async def test_append_file_success(tmp_path):
    target = tmp_path / "a.txt"
    assert await builtins.append_file(str(target), "hi") == f"Appended to {target}"
    assert target.read_text(encoding="utf-8") == "hi"


async def test_append_file_error(tmp_path):
    out = await builtins.append_file(str(tmp_path), "hi")  # directory
    assert out.startswith("Error appending to file:")


async def test_file_exists_file_dir_and_missing(tmp_path):
    f = tmp_path / "f.txt"
    f.write_text("x", encoding="utf-8")
    assert "file" in await builtins.file_exists(str(f))
    assert "dir" in await builtins.file_exists(str(tmp_path))
    assert (await builtins.file_exists(str(tmp_path / "nope"))).startswith("Not found")


async def test_file_exists_exception(monkeypatch):
    import os

    def _boom(path):
        raise OSError("cannot stat")

    monkeypatch.setattr(os.path, "exists", _boom)
    out = await builtins.file_exists("/tmp/x")
    assert out.startswith("Error checking path:")


async def test_file_info_success(tmp_path):
    f = tmp_path / "f.txt"
    f.write_text("x", encoding="utf-8")
    out = await builtins.file_info(str(f))
    assert "Size:" in out
    assert "Permissions:" in out


async def test_file_info_error():
    assert (await builtins.file_info("/nonexistent-cov3")).startswith("Error getting file info:")


# ─── group collaboration tools ──────────────────────────────────────────────


async def test_handoff_task_success(monkeypatch):
    class Engine:
        async def handoff_task(self, task_id, target, reason):
            return {"task_id": task_id, "to": target}

    monkeypatch.setattr(builtins, "_get_group_engine", lambda: Engine())
    out = await builtins.handoff_task("t1", "a2", "reason")
    assert out.startswith("Task handed off successfully:")


async def test_handoff_task_failure(monkeypatch):
    class Engine:
        async def handoff_task(self, *a, **k):
            raise RuntimeError("nope")

    monkeypatch.setattr(builtins, "_get_group_engine", lambda: Engine())
    assert (await builtins.handoff_task("t", "a")).startswith("Handoff failed:")


async def test_run_group_tasks_success(monkeypatch):
    class Engine:
        async def run_group_tasks(self, group_id):
            return {"group": group_id}

    monkeypatch.setattr(builtins, "_get_group_engine", lambda: Engine())
    assert (await builtins.run_group_tasks("g1")).startswith("Group tasks executed:")


async def test_run_group_tasks_failure(monkeypatch):
    class Engine:
        async def run_group_tasks(self, *a, **k):
            raise RuntimeError("nope")

    monkeypatch.setattr(builtins, "_get_group_engine", lambda: Engine())
    assert (await builtins.run_group_tasks("g")).startswith("Group task execution failed:")


def test_get_group_engine_delegates(monkeypatch):
    import app.core.group_collaboration as gc

    sentinel = object()
    monkeypatch.setattr(gc, "get_group_collaboration_engine", lambda: sentinel)
    assert builtins._get_group_engine() is sentinel


# ─── apply_patch ────────────────────────────────────────────────────────────


async def test_apply_patch_missing_file(tmp_path):
    out = await builtins.apply_patch(str(tmp_path / "nope.txt"), "patch")
    assert out.startswith("Error: File ")


async def test_apply_patch_dry_run_fail(tmp_path, monkeypatch):
    target = tmp_path / "f.txt"
    target.write_text("x", encoding="utf-8")

    def _run(args, **kwargs):
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="dry-run-boom")

    monkeypatch.setattr(subprocess, "run", _run)
    out = await builtins.apply_patch(str(target), "patch")
    assert out.startswith("Patch dry-run failed:")


async def test_apply_patch_success(tmp_path, monkeypatch):
    target = tmp_path / "f.txt"
    target.write_text("x", encoding="utf-8")

    def _run(args, **kwargs):
        return subprocess.CompletedProcess(args, 0, stdout="applied", stderr="")

    monkeypatch.setattr(subprocess, "run", _run)
    out = await builtins.apply_patch(str(target), "patch")
    assert out.startswith("Patch applied successfully")


async def test_apply_patch_apply_fail(tmp_path, monkeypatch):
    target = tmp_path / "f.txt"
    target.write_text("x", encoding="utf-8")
    calls = {"n": 0}

    def _run(args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="apply-boom")

    monkeypatch.setattr(subprocess, "run", _run)
    out = await builtins.apply_patch(str(target), "patch")
    assert out.startswith("Patch failed:")


async def test_apply_patch_exception(tmp_path, monkeypatch):
    target = tmp_path / "f.txt"
    target.write_text("x", encoding="utf-8")

    def _run(args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(subprocess, "run", _run)
    out = await builtins.apply_patch(str(target), "patch")
    assert out.startswith("Error applying patch:")


# ─── stream_command / container_exec ────────────────────────────────────────


async def test_stream_command_success(monkeypatch):
    import app.core.di as di

    class _Sandbox:
        async def execute(self, command):
            return f"ok:{command}"

    monkeypatch.setattr(di, "resolve", lambda name: _Sandbox())
    assert await builtins.stream_command("ls") == "ok:ls"


async def test_stream_command_error(monkeypatch):
    import app.core.di as di

    def _boom(name):
        raise RuntimeError("no sandbox")

    monkeypatch.setattr(di, "resolve", _boom)
    assert (await builtins.stream_command("ls")).startswith("Error executing command:")


def test_container_command_blocked_helper():
    assert builtins._container_command_blocked("echo hi") == ""
    blocked = builtins._container_command_blocked("echo hi; rm -rf /")
    assert blocked != ""
    assert blocked in builtins._CONTAINER_EXEC_BLOCKED_PATTERNS


async def test_container_exec_blocked_pattern():
    out = await builtins.container_exec("c1", "echo a && echo b")
    assert out.startswith("Command rejected: dangerous pattern detected")


async def test_container_exec_no_output(tmp_path, monkeypatch):
    def _run(args, **kwargs):
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _run)
    assert await builtins.container_exec("c1", "echo hi", workdir="/srv") == "(no output)"


async def test_container_exec_output(tmp_path, monkeypatch):
    captured = {}

    def _run(args, **kwargs):
        captured["args"] = args
        return subprocess.CompletedProcess(args, 0, stdout="hi", stderr="")

    monkeypatch.setattr(subprocess, "run", _run)
    assert await builtins.container_exec("c1", "echo hi", workdir="/srv") == "hi"
    assert captured["args"] == ["docker", "exec", "-w", "/srv", "c1", "sh", "-c", "echo hi"]


async def test_container_exec_nonzero_exit(monkeypatch):
    def _run(args, **kwargs):
        return subprocess.CompletedProcess(args, 2, stdout="", stderr="boom")

    monkeypatch.setattr(subprocess, "run", _run)
    out = await builtins.container_exec("c1", "false")
    assert out == "Container exec failed (exit 2):\nboom"


async def test_container_exec_docker_missing(monkeypatch):
    def _run(*a, **k):
        raise FileNotFoundError("docker")

    monkeypatch.setattr(subprocess, "run", _run)
    out = await builtins.container_exec("c1", "echo hi")
    assert out == "Error: Docker is not installed or not in PATH"


async def test_container_exec_generic_error(monkeypatch):
    def _run(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(subprocess, "run", _run)
    out = await builtins.container_exec("c1", "echo hi")
    assert out.startswith("Error executing in container:")


# ─── analyze_error / simulate_experiment ────────────────────────────────────


async def test_analyze_error_success():
    out = await builtins.analyze_error("ModuleNotFoundError: No module named 'x'", "{}")
    data = json.loads(out)
    assert "cause" in data


async def test_analyze_error_invalid_context():
    out = await builtins.analyze_error("boom", "{not json")
    assert out.startswith("Error analyzing error:")


async def test_simulate_experiment(monkeypatch):
    import app.simulation.experiments as exp

    monkeypatch.setattr(exp, "run_experiment", lambda model, **params: f'{{"model": "{model}"}}')
    assert await builtins.simulate_experiment("heat", alpha=1) == '{"model": "heat"}'

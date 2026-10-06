"""Coverage tests for app.tools.native_tools (no real network/browser)."""

from __future__ import annotations

import asyncio
import sys
import types
from types import SimpleNamespace

import pytest

from app.tools import native_tools

# ─── helpers / fakes ────────────────────────────────────────────────────────


class FakeProc:
    def __init__(self, stdout=b"", stderr=b"", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode

    async def communicate(self):
        return self.stdout, self.stderr


class FakeResponse:
    def __init__(self, *, text="", content=b"", status_code=200, is_redirect=False, headers=None):
        self.text = text
        self.content = content
        self.status_code = status_code
        self.is_redirect = is_redirect
        self.headers = headers or {}
        self.raised = False

    def raise_for_status(self):
        self.raised = True


class FakeHTTPClient:
    """Minimal httpx.AsyncClient stand-in (sync ctor, async ctx + verbs)."""

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
        self.post_calls.append((url, kwargs))
        return self._next()


# ─── native_run ─────────────────────────────────────────────────────────────


async def test_native_run_rejects_dangerous_command():
    out = await native_tools.native_run("echo a; echo b")
    assert out.startswith("Command rejected:")
    assert "dangerous shell pattern" in out


async def test_native_run_rejects_empty_command():
    assert await native_tools.native_run("") == "Error: empty command"


async def test_native_run_rejects_disallowed_binary():
    out = await native_tools.native_run("python3 -c print")
    assert out == "Command rejected: 'python3' is not in the allowed binaries list"


async def test_native_run_rejects_rm_dangerous_flags():
    out = await native_tools.native_run("rm -rf /tmp/whatever")
    assert out.startswith("Command rejected: dangerous rm flags detected")


async def test_native_run_rejects_rm_system_path():
    out = await native_tools.native_run("rm /etc/passwd")
    assert out.startswith("Command rejected: rm targeting system path")


async def test_native_run_rm_safe_targets(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    (tmp_path / "b.txt").write_text("y", encoding="utf-8")
    out = await native_tools.native_run("rm a.txt b.txt")
    assert "[exit code:" not in out
    assert not (tmp_path / "a.txt").exists()


async def test_native_run_success():
    out = await native_tools.native_run("echo hello")
    assert "hello" in out


async def test_native_run_reports_exit_code_and_stderr():
    out = await native_tools.native_run("cat /tmp/does-not-exist-cov3-file")
    assert "[exit code:" in out or "[stderr]:" in out


async def _timeout_wait_for(coro, *args, **kwargs):
    if hasattr(coro, "close"):
        coro.close()
    raise TimeoutError


async def test_native_run_timeout(monkeypatch):
    monkeypatch.setattr(asyncio, "wait_for", _timeout_wait_for)
    out = await native_tools.native_run("echo hi", timeout=1)
    assert out == "TIMEOUT: Command exceeded 1s limit"


async def test_native_run_generic_exception():
    out = await native_tools.native_run("echo hi", cwd="/nonexistent-cov3-dir")
    assert out.startswith("Error:")


# ─── file tools ─────────────────────────────────────────────────────────────


async def test_native_read_file_rejects_system_path():
    out = await native_tools.native_read_file("/etc/passwd")
    assert out.startswith("Error: Access denied")


async def test_native_read_file_success(tmp_path):
    target = tmp_path / "f.txt"
    target.write_text("content-here", encoding="utf-8")
    assert await native_tools.native_read_file(str(target)) == "content-here"


async def test_native_read_file_exception(tmp_path):
    out = await native_tools.native_read_file(str(tmp_path))  # directory
    assert out.startswith("Error reading")


async def test_native_write_file_rejects_system_path():
    out = await native_tools.native_write_file("/etc/evil", "x")
    assert out.startswith("Error: Access denied")


async def test_native_write_file_creates_dirs(tmp_path):
    target = tmp_path / "nested" / "dir" / "f.txt"
    out = await native_tools.native_write_file(str(target), "abc")
    assert out == f"Written 3 chars to {target}"
    assert target.read_text(encoding="utf-8") == "abc"


async def test_native_write_file_relative_no_dirname(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = await native_tools.native_write_file("plain.txt", "z")
    assert out == "Written 1 chars to plain.txt"
    assert (tmp_path / "plain.txt").read_text(encoding="utf-8") == "z"


async def test_native_write_file_exception(tmp_path, monkeypatch):
    def _boom(*args, **kwargs):
        raise OSError("nope")

    monkeypatch.setattr(native_tools.os, "makedirs", _boom)
    out = await native_tools.native_write_file(str(tmp_path / "sub" / "f.txt"), "x")
    assert out.startswith("Error writing")


async def test_native_list_dir_success(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    out = await native_tools.native_list_dir(str(tmp_path))
    assert "[DIR] sub" in out
    assert "[FILE] a.txt" in out


async def test_native_list_dir_empty(tmp_path):
    assert await native_tools.native_list_dir(str(tmp_path)) == "(empty directory)"


async def test_native_list_dir_error():
    out = await native_tools.native_list_dir("/nonexistent-cov3-dir")
    assert out.startswith("Error listing")


# ─── browser / GUI tools ────────────────────────────────────────────────────


async def test_open_browser_success(monkeypatch):
    opened = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url) or True)
    assert (
        await native_tools.open_browser("http://example.com")
        == "Opened http://example.com in browser"
    )
    assert opened == ["http://example.com"]


async def test_open_browser_error(monkeypatch):
    def _boom(url):
        raise RuntimeError("no browser")

    monkeypatch.setattr("webbrowser.open", _boom)
    out = await native_tools.open_browser("http://example.com")
    assert out.startswith("Error:")


async def test_take_screenshot_with_pyautogui(monkeypatch, tmp_path):
    saved = {}

    class _Img:
        def save(self, path):
            saved["path"] = path

    fake = types.ModuleType("pyautogui")
    fake.screenshot = lambda: _Img()
    monkeypatch.setitem(sys.modules, "pyautogui", fake)

    out = await native_tools.take_screenshot(str(tmp_path / "s.png"))
    assert out == str(tmp_path / "s.png")
    assert saved["path"] == str(tmp_path / "s.png")


async def test_take_screenshot_fallback_screencapture(monkeypatch):
    monkeypatch.setitem(sys.modules, "pyautogui", None)  # force ImportError
    calls = []
    monkeypatch.setattr(
        native_tools.subprocess,
        "run",
        lambda *a, **k: calls.append(a) or SimpleNamespace(returncode=0),
    )
    out = await native_tools.take_screenshot("/tmp/shot.png")
    assert out == "/tmp/shot.png"
    assert calls


async def test_take_screenshot_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "pyautogui", None)

    def _boom(*a, **k):
        raise RuntimeError("no screencapture")

    monkeypatch.setattr(native_tools.subprocess, "run", _boom)
    out = await native_tools.take_screenshot()
    assert out.startswith("Error taking screenshot:")


async def test_click_mouse_success(monkeypatch):
    calls = []
    fake = types.ModuleType("pyautogui")
    fake.click = lambda x, y, button="left": calls.append((x, y, button))
    monkeypatch.setitem(sys.modules, "pyautogui", fake)
    assert await native_tools.click_mouse(3, 4) == "Clicked (3, 4)"
    assert calls == [(3, 4, "left")]


async def test_click_mouse_import_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "pyautogui", None)
    out = await native_tools.click_mouse(1, 2)
    assert "pyautogui not installed" in out


async def test_click_mouse_error(monkeypatch):
    fake = types.ModuleType("pyautogui")

    def _boom(*a, **k):
        raise RuntimeError("bad")

    fake.click = _boom
    monkeypatch.setitem(sys.modules, "pyautogui", fake)
    out = await native_tools.click_mouse(1, 2)
    assert out.startswith("Error:")


async def test_type_text_success(monkeypatch):
    calls = []
    fake = types.ModuleType("pyautogui")
    fake.typewrite = lambda text, interval=0.02: calls.append((text, interval))
    monkeypatch.setitem(sys.modules, "pyautogui", fake)
    assert await native_tools.type_text("abc") == "Typed 3 chars"
    assert calls == [("abc", 0.02)]


async def test_type_text_import_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "pyautogui", None)
    out = await native_tools.type_text("abc")
    assert "pyautogui not installed" in out


async def test_type_text_error(monkeypatch):
    fake = types.ModuleType("pyautogui")

    def _boom(*a, **k):
        raise RuntimeError("bad")

    fake.typewrite = _boom
    monkeypatch.setitem(sys.modules, "pyautogui", fake)
    out = await native_tools.type_text("abc")
    assert out.startswith("Error:")


# ─── media processing ───────────────────────────────────────────────────────


async def test_process_video_prepends_prefix_and_returns_stderr(monkeypatch):
    captured = {}

    async def _exec(*args, **kwargs):
        captured["args"] = args
        return FakeProc(stderr=b"video done")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _exec)
    out = await native_tools.process_video("-i in.mp4 out.mp4")
    assert out == "video done"
    assert captured["args"][0] == "ffmpeg"


async def test_process_video_existing_prefix_no_duplicate(monkeypatch):
    captured = {}

    async def _exec(*args, **kwargs):
        captured["args"] = args
        return FakeProc(stderr=b"")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _exec)
    out = await native_tools.process_video("ffmpeg -i in.mp4 out.mp4")
    assert out == "Video processing completed"
    assert captured["args"][0] == "ffmpeg"


async def test_process_video_timeout(monkeypatch):
    async def _exec(*args, **kwargs):
        return FakeProc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _exec)
    monkeypatch.setattr(asyncio, "wait_for", _timeout_wait_for)
    out = await native_tools.process_video("-i in.mp4 out.mp4")
    assert out == "TIMEOUT: Video processing exceeded 5 minutes"


async def test_process_video_exception(monkeypatch):
    async def _boom(*args, **kwargs):
        raise FileNotFoundError("ffmpeg")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _boom)
    out = await native_tools.process_video("-i in.mp4 out.mp4")
    assert out.startswith("Error:")


async def test_process_image_prepends_prefix(monkeypatch):
    captured = {}

    async def _exec(*args, **kwargs):
        captured["args"] = args
        return FakeProc(stdout=b"ok", stderr=b"warn")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _exec)
    out = await native_tools.process_image("in.png out.png")
    assert captured["args"][0] == "convert"
    assert out == "ok\nwarn"


async def test_process_image_empty_output(monkeypatch):
    async def _exec(*args, **kwargs):
        return FakeProc(stdout=b"", stderr=b"")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _exec)
    assert await native_tools.process_image("convert a b") == "Image processing completed"


async def test_process_image_timeout(monkeypatch):
    async def _exec(*args, **kwargs):
        return FakeProc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _exec)
    monkeypatch.setattr(asyncio, "wait_for", _timeout_wait_for)
    out = await native_tools.process_image("a b")
    assert out == "TIMEOUT: Image processing exceeded 60s"


async def test_process_image_exception(monkeypatch):
    async def _boom(*args, **kwargs):
        raise FileNotFoundError("convert")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _boom)
    out = await native_tools.process_image("a b")
    assert out.startswith("Error:")


# ─── web search / download ──────────────────────────────────────────────────


async def test_native_web_search_parses_results(monkeypatch):
    html = '<a rel="nofollow" class="result__a" href="http://x">Title X</a>'
    import httpx

    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kw: FakeHTTPClient(responses=[FakeResponse(text=html)])
    )
    out = await native_tools.native_web_search("q")
    assert "Title X" in out
    assert "http://x" in out


async def test_native_web_search_no_results(monkeypatch):
    import httpx

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: FakeHTTPClient(responses=[FakeResponse(text="<html></html>")]),
    )
    assert await native_tools.native_web_search("q") == "No results found"


async def test_native_web_search_error(monkeypatch):
    import httpx

    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kw: FakeHTTPClient(error=RuntimeError("down"))
    )
    out = await native_tools.native_web_search("q")
    assert out.startswith("Error searching:")


async def test_download_file_blocked(monkeypatch):
    import app.utils.ssrf as ssrf

    monkeypatch.setattr(ssrf, "blocked_reason", lambda url: "private ip")
    out = await native_tools.download_file("http://10.0.0.1/x", "/tmp/x")
    assert out.startswith("Error downloading: blocked")


async def test_download_file_success(monkeypatch, tmp_path):
    import httpx

    import app.utils.ssrf as ssrf

    monkeypatch.setattr(ssrf, "blocked_reason", lambda url: "")
    client = FakeHTTPClient(responses=[FakeResponse(content=b"payload")])
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: client)
    target = tmp_path / "out.bin"
    out = await native_tools.download_file("http://example.com/a", str(target))
    assert out == f"Downloaded 7 bytes to {target}"
    assert target.read_bytes() == b"payload"


async def test_download_file_relative_output(monkeypatch, tmp_path):
    import httpx

    import app.utils.ssrf as ssrf

    monkeypatch.setattr(ssrf, "blocked_reason", lambda url: "")
    monkeypatch.chdir(tmp_path)
    client = FakeHTTPClient(responses=[FakeResponse(content=b"data")])
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: client)
    out = await native_tools.download_file("http://example.com/a", "out.bin")
    assert out == "Downloaded 4 bytes to out.bin"
    assert (tmp_path / "out.bin").read_bytes() == b"data"


async def test_download_file_relative_redirect(monkeypatch, tmp_path):
    import httpx

    import app.utils.ssrf as ssrf

    monkeypatch.setattr(ssrf, "blocked_reason", lambda url: "")
    responses = [
        FakeResponse(is_redirect=True, headers={"location": "/next"}),
        FakeResponse(content=b"ok"),
    ]
    client = FakeHTTPClient(responses=responses)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: client)
    target = tmp_path / "out.bin"
    out = await native_tools.download_file("http://example.com/a", str(target))
    assert out.startswith("Downloaded 2 bytes")
    assert client.get_calls[-1] == "http://example.com/next"


async def test_download_file_absolute_redirect(monkeypatch, tmp_path):
    import httpx

    import app.utils.ssrf as ssrf

    monkeypatch.setattr(ssrf, "blocked_reason", lambda url: "")
    responses = [
        FakeResponse(is_redirect=True, headers={"location": "https://cdn.example.com/f"}),
        FakeResponse(content=b"z"),
    ]
    client = FakeHTTPClient(responses=responses)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: client)
    target = tmp_path / "out.bin"
    out = await native_tools.download_file("http://example.com/a", str(target))
    assert out.startswith("Downloaded 1 bytes")
    assert client.get_calls[-1] == "https://cdn.example.com/f"


async def test_download_file_redirect_blocked(monkeypatch, tmp_path):
    import httpx

    import app.utils.ssrf as ssrf

    calls = {"n": 0}

    def _blocked(url):
        calls["n"] += 1
        return "" if calls["n"] == 1 else "blocked redirect"

    monkeypatch.setattr(ssrf, "blocked_reason", _blocked)
    client = FakeHTTPClient(
        responses=[FakeResponse(is_redirect=True, headers={"location": "http://internal/x"})]
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: client)
    out = await native_tools.download_file("http://example.com/a", str(tmp_path / "o.bin"))
    assert out.startswith("Error downloading: blocked redirect")


async def test_download_file_too_many_redirects(monkeypatch, tmp_path):
    import httpx

    import app.utils.ssrf as ssrf

    monkeypatch.setattr(ssrf, "blocked_reason", lambda url: "")
    responses = [FakeResponse(is_redirect=True, headers={"location": "/loop"}) for _ in range(5)]
    client = FakeHTTPClient(responses=responses)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: client)
    out = await native_tools.download_file("http://example.com/a", str(tmp_path / "o.bin"))
    assert out == "Error downloading: too many redirects"


async def test_download_file_exception(monkeypatch, tmp_path):
    import httpx

    import app.utils.ssrf as ssrf

    monkeypatch.setattr(ssrf, "blocked_reason", lambda url: "")
    client = FakeHTTPClient(error=RuntimeError("network"))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: client)
    out = await native_tools.download_file("http://example.com/a", str(tmp_path / "o.bin"))
    assert out.startswith("Error downloading:")


# ─── validation helpers ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "command",
    ["a; b", "a | b", "a $(b)", "a `b`", "a && b", "a || b"],
)
def test_validate_command_safety_rejects(command):
    safe, reason = native_tools._validate_command_safety(command)
    assert safe is False
    assert "dangerous shell pattern" in reason


def test_validate_command_safety_allows():
    assert native_tools._validate_command_safety("echo hello") == (True, "OK")


def test_get_workspace_root_env(monkeypatch):
    monkeypatch.setenv("CLIMBER_SANDBOX_WORKDIR", "/custom/root")
    assert native_tools._get_workspace_root() == "/custom/root"
    monkeypatch.delenv("CLIMBER_SANDBOX_WORKDIR", raising=False)
    assert native_tools._get_workspace_root() == "/workspace"


def test_validate_path_within_workspace(monkeypatch):
    monkeypatch.setenv("CLIMBER_SANDBOX_WORKDIR", "/workspace")
    assert native_tools._validate_path_within_workspace("/workspace/../etc") == (
        False,
        "Path traversal detected",
    )
    assert native_tools._validate_path_within_workspace("/etc/passwd") == (
        False,
        "Path is outside workspace",
    )
    assert native_tools._validate_path_within_workspace("/workspace/sub/f") == (True, "OK")


def test_validate_file_path_blocked_prefixes():
    for path in ("/etc/passwd", "/root/x", "/home/u", "/proc/1/environ", "/dev/null", "/sys/x"):
        valid, reason = native_tools._validate_file_path(path)
        assert valid is False
        assert "blocked system directory" in reason


def test_validate_file_path_outside_allowed():
    valid, reason = native_tools._validate_file_path("/var/log/x")
    assert valid is False
    assert "outside allowed directories" in reason


def test_validate_file_path_allowed_and_writable_dir(tmp_path):
    valid, _ = native_tools._validate_file_path(str(tmp_path / "new.txt"))
    assert valid is True
    # writable=True on an existing directory is rejected.
    valid2, reason2 = native_tools._validate_file_path(str(tmp_path), writable=True)
    assert valid2 is False
    assert "not a regular file" in reason2

"""Native execution tools — unrestricted system access for autonomous agents.

These tools require explicit user permission (native_mode=True in session config).
When enabled, the agent can:
- Run any shell command without sandbox restrictions
- Read/write any file on the system
- Open URLs in the browser
- Take screenshots
- Control mouse and keyboard
- Process media (video/audio/image)
"""

from __future__ import annotations

import asyncio
import os
import re
import shlex
import shutil
import subprocess
import urllib.parse
from collections.abc import Callable
from pathlib import Path
from typing import Any

import structlog

from app.tools import tool

logger = structlog.get_logger()


def _pyautogui_available() -> bool:
    """Whether to prefer pyautogui for desktop interaction.

    pyautogui import can block indefinitely under some headless X setups,
    so this stays disabled; the xdotool/scrot fallbacks are reliable.
    """
    return False


async def _pyautogui_call(call: Callable[[], Any], timeout: float = 8.0) -> Any:
    """Run a blocking pyautogui call in a worker thread with a hard timeout."""
    try:
        return await asyncio.wait_for(asyncio.to_thread(call), timeout=timeout)
    except Exception:
        raise


@tool(description="Run a shell command with system access. Subject to sandbox restrictions.")
async def native_run(command: str, timeout: int = 120, cwd: str | None = None) -> str:
    """Run a shell command with native system access."""
    safe, reason = _validate_command_safety(command)
    if not safe:
        return f"Command rejected: {reason}"

    try:
        args = shlex.split(command)
        if not args:
            return "Error: empty command"

        base = os.path.basename(args[0])
        allowed_binaries = {
            "ls", "cat", "echo", "pwd", "mkdir", "cp", "mv", "rm",
            "touch", "head", "tail", "grep", "find", "wc", "sort", "uniq",
            "diff", "file", "which", "env", "git", "curl", "wget",
            "tar", "zip", "unzip", "chmod", "chown", "ln", "tee", "awk",
            "sed", "xargs", "jq", "make", "pytest",
            "ffmpeg", "ffprobe", "ffplay", "convert", "magick", "identify",
            "xdotool", "import", "scrot", "xdg-open", "google-chrome",
        }
        if base not in allowed_binaries:
            return f"Command rejected: '{base}' is not in the allowed binaries list"

        # Block dangerous argument patterns for sensitive commands
        if base == "rm":
            full_args = " ".join(args[1:])
            for pattern in [r"-[rR][fF]", r"-[fF][rR]", r"-r\s+-?[fF]", r"-[fF]\s+-?r",
                            r"--recursive.*--force", r"--force.*--recursive"]:
                if re.search(pattern, full_args):
                    return f"Command rejected: dangerous rm flags detected ({full_args})"
            # Block rm targeting root or system paths (allow /workspace, /tmp)
            target_paths = [p for p in full_args.split() if not p.startswith('-')]
            for tp in target_paths:
                abs_tp = os.path.abspath(tp)
                if abs_tp == '/' or abs_tp.startswith('/etc') or abs_tp.startswith('/root') or abs_tp.startswith('/home'):
                    return f"Command rejected: rm targeting system path ({full_args})"

        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        output = stdout.decode("utf-8", errors="replace")[:10000]
        if stderr:
            output += f"\n[stderr]: {stderr.decode('utf-8', errors='replace')[:2000]}"
        if proc.returncode != 0:
            output += f"\n[exit code: {proc.returncode}]"
        return output if output else "Command completed (no output)"
    except TimeoutError:
        return f"TIMEOUT: Command exceeded {timeout}s limit"
    except Exception as e:
        return f"Error: {e!s}"


@tool(
    description="Read any file from the system. Returns file content as text.",
    sandbox_safe_when_unavailable=True,
)
async def native_read_file(path: str) -> str:
    """Read any file from the filesystem."""
    valid, reason = _validate_file_path(path, writable=False)
    if not valid:
        return f"Error: {reason}"
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            content = f.read()
        return content[:50000]
    except Exception as e:
        return f"Error reading {path}: {e!s}"


@tool(description="Write content to any file path. Creates directories if needed.")
async def native_write_file(path: str, content: str) -> str:
    """Write content to file."""
    valid, reason = _validate_file_path(path, writable=True)
    if not valid:
        return f"Error: {reason}"
    try:
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Written {len(content)} chars to {path}"
    except Exception as e:
        return f"Error writing {path}: {e!s}"


@tool(
    description="List files and directories at a given path.",
    sandbox_safe_when_unavailable=True,
)
async def native_list_dir(path: str = ".") -> str:
    """List directory contents."""
    valid, reason = _validate_path_within_workspace(path)
    if not valid:
        return f"Error: {reason}"
    try:
        entries = []
        for item in sorted(os.listdir(path)):
            full = os.path.join(path, item)
            is_dir = os.path.isdir(full)
            size = os.path.getsize(full) if not is_dir else 0
            prefix = "[DIR] " if is_dir else "[FILE] "
            suffix = "" if is_dir else f" ({size:,} bytes)"
            entries.append(f"{prefix}{item}{suffix}")
        return "\n".join(entries) if entries else "(empty directory)"
    except Exception as e:
        return f"Error listing {path}: {e!s}"


@tool(description="Open a URL in the default web browser.")
async def open_browser(url: str) -> str:
    """Open URL in default browser."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return "Error: URL must include an http or https scheme and host"
    try:
        import webbrowser
        if webbrowser.open(url):
            return f"Opened {url} in browser"
        if os.environ.get("DISPLAY"):
            for opener in ("xdg-open",):
                try:
                    subprocess.run([opener, url], check=True, timeout=15)
                    return f"Opened {url} via {opener}"
                except (FileNotFoundError, subprocess.CalledProcessError):
                    continue
        for chrome in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
            if shutil.which(chrome):
                proc = await asyncio.create_subprocess_exec(
                    chrome, "--headless=new", "--no-sandbox", "--disable-gpu",
                    "--no-first-run", "--dump-dom", url,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                try:
                    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
                except TimeoutError:
                    proc.kill()
                    return f"Opened {url} in headless {chrome} (dump timed out)"
                return f"Opened {url} in headless {chrome} (DOM: {len(stdout.decode('utf-8', errors='replace'))} chars)"
        return f"Error: no browser available to open {url}"
    except Exception as e:
        return f"Error: {e!s}"


@tool(description="Take a screenshot of the screen. Returns the saved file path.")
async def take_screenshot(output_path: str = "/tmp/screenshot.png") -> str:
    """Take a screenshot."""
    try:
        if _pyautogui_available():
            try:
                img = await _pyautogui_call(lambda: __import__("pyautogui").screenshot())
                img.save(output_path)
                return output_path
            except Exception as e:
                logger.debug("native.screenshot_pyautogui_unavailable", error=str(e))
        if not os.environ.get("DISPLAY"):
            return "Error taking screenshot: no DISPLAY available (run under Xvfb or a real desktop)"
        for cmd in (["scrot", output_path], ["import", "-window", "root", output_path], ["screencapture", output_path]):
            try:
                subprocess.run(cmd, check=True, timeout=15)
                return output_path
            except (FileNotFoundError, subprocess.CalledProcessError):
                continue
        return "Error taking screenshot: no working screenshot tool found"
    except Exception as e:
        return f"Error taking screenshot: {e!s}"


@tool(description="Click at x,y coordinates on screen.")
async def click_mouse(x: int, y: int, button: str = "left") -> str:
    """Click mouse at coordinates."""
    try:
        if _pyautogui_available():
            try:
                await _pyautogui_call(lambda: __import__("pyautogui").click(x, y, button=button))
                return f"Clicked ({x}, {y})"
            except Exception as e:
                logger.debug("native.click_pyautogui_unavailable", error=str(e))
        if not os.environ.get("DISPLAY"):
            return "Error clicking: no DISPLAY available (run under Xvfb or a real desktop)"
        subprocess.run(["xdotool", "mousemove", str(x), str(y), "click", "1" if button == "left" else "3"], check=True, timeout=10)
        return f"Clicked ({x}, {y})"
    except Exception as e:
        return f"Error: {e!s}"


@tool(description="Type text at the current cursor position.")
async def type_text(text: str, interval: float = 0.02) -> str:
    """Type text using keyboard."""
    try:
        if _pyautogui_available():
            try:
                await _pyautogui_call(lambda: __import__("pyautogui").typewrite(text, interval=interval))
                return f"Typed {len(text)} chars"
            except Exception as e:
                logger.debug("native.type_pyautogui_unavailable", error=str(e))
        if not os.environ.get("DISPLAY"):
            return "Error typing: no DISPLAY available (run under Xvfb or a real desktop)"
        subprocess.run(["xdotool", "type", "--delay", str(int(interval * 1000)), text], check=True, timeout=15)
        return f"Typed {len(text)} chars"
    except Exception as e:
        return f"Error: {e!s}"


@tool(description="Process video with ffmpeg. Example: cut segment, convert format, extract audio.")
async def process_video(command: str) -> str:
    """Run ffmpeg command. The 'ffmpeg' prefix is added automatically if not present."""
    try:
        if not command.startswith("ffmpeg"):
            command = f"ffmpeg {command}"
        args = shlex.split(command)
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        output = ""
        out_text = stdout.decode("utf-8", errors="replace").strip()
        if out_text:
            output += out_text[:3000]
        err_text = stderr.decode("utf-8", errors="replace").strip()
        if err_text:
            if output:
                output += "\n"
            output += err_text[:2000]
        return output if output else "Video processing completed"
    except TimeoutError:
        return "TIMEOUT: Video processing exceeded 5 minutes"
    except Exception as e:
        return f"Error: {e!s}"


@tool(description="Process image with ImageMagick convert command.")
async def process_image(command: str) -> str:
    """Run ImageMagick convert command."""
    try:
        if not command.startswith("convert"):
            command = f"convert {command}"
        args = shlex.split(command)
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        output = stdout.decode("utf-8", errors="replace")[:2000]
        err = stderr.decode("utf-8", errors="replace")[:2000]
        if err:
            output += f"\n{err}"
        return output if output else "Image processing completed"
    except TimeoutError:
        return "TIMEOUT: Image processing exceeded 60s"
    except Exception as e:
        return f"Error: {e!s}"


@tool(description="Search the web using a search engine. Returns top results (native mode — enhanced with num_results).")
async def native_web_search(query: str, num_results: int = 10) -> str:
    """Search the web with enhanced result count (native mode only)."""
    try:
        import re

        import httpx
        url = "https://html.duckduckgo.com/html/"
        resp = await httpx.AsyncClient(timeout=15).post(url, data={"q": query})
        results = re.findall(
            r'<a rel="nofollow" class="result__a" href="([^"]+)">([^<]+)</a>',
            resp.text,
        )
        formatted = []
        for href, title in results[:num_results]:
            formatted.append(f"- {title.strip()}\n  {href}")
        return "\n".join(formatted) if formatted else "No results found"
    except Exception as e:
        return f"Error searching: {e!s}"


@tool(description="Download a file from URL to a local path.")
async def download_file(url: str, output_path: str) -> str:
    """Download file from URL."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            dir_name = os.path.dirname(output_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(resp.content)
        return f"Downloaded {len(resp.content):,} bytes to {output_path}"
    except Exception as e:
        return f"Error downloading: {e!s}"


# ─── Security validation helpers ──────────────────────────────────────────

# Dangerous shell patterns that indicate command injection
_DANGEROUS_SHELL_PATTERNS = [
    r';',           # semicolon chaining
    r'\|',          # pipe
    r'\$\(',        # $() command substitution
    r'`',           # backtick command substitution
    r'&&',          # logical AND chaining
    r'\|\|',        # logical OR chaining
]


def _validate_command_safety(command: str) -> tuple[bool, str]:
    """Check if a shell command contains dangerous patterns.

    Returns (is_safe, reason) where reason explains the result.
    """
    for pattern in _DANGEROUS_SHELL_PATTERNS:
        if re.search(pattern, command):
            return False, f"dangerous shell pattern detected: {pattern}"
    return True, "OK"


def _get_workspace_root() -> str:
    """Get the workspace root directory."""
    return os.environ.get("CLIMBER_SANDBOX_WORKDIR", "/workspace")


def _resolve_within_workspace(path: str) -> tuple[bool, str]:
    """Resolve path (including symlinks) and check ancestry within workspace roots.

    Uses Path.resolve() to follow symlinks, then relative_to() for exact
    ancestry instead of string prefix matching.

    Returns (is_within, resolved_or_reason).
    """
    workspace_root = _get_workspace_root()
    abs_workspace = os.path.abspath(workspace_root)

    try:
        resolved = Path(path).expanduser().resolve(strict=False)
    except (OSError, RuntimeError, ValueError) as exc:
        return False, f"Access denied: cannot resolve path '{path}': {exc}"

    for root in (abs_workspace, "/tmp"):
        try:
            resolved.relative_to(root)
            return True, str(resolved)
        except ValueError:
            continue

    return False, f"Access denied: resolved path '{resolved}' is outside workspace"


def _validate_path_within_workspace(path: str) -> tuple[bool, str]:
    """Validate that a path is within the workspace directory.

    Uses Path.resolve() for symlink-safe ancestry check.
    Returns (is_valid, message) where message explains the result.
    """
    ok, result = _resolve_within_workspace(path)
    if not ok:
        return False, result
    return True, "OK"


_BLOCKED_PREFIXES = (
    "/etc", "/root", "/home",
    "/proc/", "/sys/", "/dev/",
)


def _validate_file_path(path: str, writable: bool = False) -> tuple[bool, str]:
    """Validate file path is within allowed directories and not in blocked system paths.

    Uses Path.resolve() for symlink-safe ancestry check.
    Returns (is_valid, message).
    """

    abs_path = os.path.abspath(path)

    for blocked in _BLOCKED_PREFIXES:
        normalized = blocked.rstrip("/")
        if abs_path == normalized or abs_path.startswith(normalized + "/"):
            return False, f"Access denied: path '{abs_path}' is in a blocked system directory"

    ok, result = _resolve_within_workspace(path)
    if not ok:
        return False, result

    if writable and os.path.exists(abs_path) and not os.path.isfile(abs_path):
        return False, f"Path '{abs_path}' is not a regular file"

    return True, "OK"

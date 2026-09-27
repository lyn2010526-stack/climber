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
import tempfile
import urllib.parse
from pathlib import Path

import structlog

from app.tools import redact_error_text, tool
from app.utils.ssrf import blocked_reason

logger = structlog.get_logger()

# Absolute path of the screenshot binary, resolved once so a writable PATH
# entry ahead of the real binary cannot substitute another executable.
# None means "unavailable" and the screenshot call is skipped.
_SCREENSHOT_BIN: str | None = shutil.which("screencapture")

# Default screenshot target, resolved from the platform temp directory so no
# shared, guessable path is hardcoded. The value is unchanged on a default
# Linux install; the directory is still world-writable, so callers that need
# confidentiality should pass their own private path.
_DEFAULT_SCREENSHOT_PATH: str = str(Path(tempfile.gettempdir()) / "screenshot.png")


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
                if abs_tp == '/' or abs_tp.startswith(('/etc', '/root', '/home')):
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
        return f"Error: {redact_error_text(e)}"


@tool(description="Open a URL in the default web browser.")
async def open_browser(url: str) -> str:
    """Open URL in default browser."""
    try:
        reason = blocked_reason(url)
        if reason is not None:
            return f"Error: request blocked by SSRF protection ({reason})"
        import webbrowser
        webbrowser.open(url)
        return f"Opened {url} in browser"
    except Exception as e:
        return f"Error: {redact_error_text(e)}"


@tool(description="Take a screenshot of the screen. Returns the saved file path.")
async def take_screenshot(output_path: str = _DEFAULT_SCREENSHOT_PATH) -> str:
    """Take a screenshot."""
    try:
        try:
            import pyautogui
            img = pyautogui.screenshot()
            img.save(output_path)
            return output_path
        except ImportError:
            pass
        if _SCREENSHOT_BIN is None:
            return "Error taking screenshot: screencapture is not available on this platform"
        # S603 audit: argv is the resolved binary plus the caller's destination
        # path as one argument. shell=False, so a crafted path is a path, never a
        # command word.
        subprocess.run([_SCREENSHOT_BIN, output_path], check=True, timeout=10)  # noqa: S603  # argv[0] is an absolute path from shutil.which()
        return output_path
    except Exception as e:
        return f"Error taking screenshot: {redact_error_text(e)}"


@tool(description="Click at x,y coordinates on screen.")
async def click_mouse(x: int, y: int, button: str = "left") -> str:
    """Click mouse at coordinates."""
    try:
        import pyautogui
        pyautogui.click(x, y, button=button)
        return f"Clicked ({x}, {y})"
    except ImportError:
        return "pyautogui not installed. Install with: pip install pyautogui"
    except Exception as e:
        return f"Error: {redact_error_text(e)}"


@tool(description="Type text at the current cursor position.")
async def type_text(text: str, interval: float = 0.02) -> str:
    """Type text using keyboard."""
    try:
        import pyautogui
        pyautogui.typewrite(text, interval=interval)
        return f"Typed {len(text)} chars"
    except ImportError:
        return "pyautogui not installed. Install with: pip install pyautogui"
    except Exception as e:
        return f"Error: {redact_error_text(e)}"


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
        _stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        output = stderr.decode("utf-8", errors="replace")[:5000]
        return output if output else "Video processing completed"
    except TimeoutError:
        return "TIMEOUT: Video processing exceeded 5 minutes"
    except Exception as e:
        return f"Error: {redact_error_text(e)}"


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
        return f"Error: {redact_error_text(e)}"


@tool(description="Download a file from URL to a local path.")
async def download_file(url: str, output_path: str) -> str:
    """Download file from URL."""
    try:
        reason = blocked_reason(url)
        if reason is not None:
            return f"Error downloading: request blocked by SSRF protection ({reason})"
        import httpx
        # Redirects are followed manually: every hop has to pass the SSRF
        # policy on its own before the client is allowed to request it.
        async with httpx.AsyncClient(timeout=60, follow_redirects=False) as client:
            current_url = url
            resp = None
            for _hop in range(5):
                resp = await client.get(current_url)
                if resp.is_redirect and resp.headers.get("location"):
                    next_url = str(resp.headers["location"])
                    if not next_url.startswith(("http://", "https://")):
                        next_url = urllib.parse.urljoin(current_url, next_url)
                    next_reason = blocked_reason(next_url)
                    if next_reason is not None:
                        return f"Error downloading: blocked redirect ({next_reason})"
                    current_url = next_url
                    continue
                break
            resp.raise_for_status()
            dir_name = os.path.dirname(output_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(resp.content)
        return f"Downloaded {len(resp.content):,} bytes to {output_path}"
    except Exception as e:
        return f"Error downloading: {redact_error_text(e)}"


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


def _validate_path_within_workspace(path: str) -> tuple[bool, str]:
    """Validate that a path is within the workspace directory.

    Returns (is_valid, message) where message explains the result.
    """
    workspace_root = _get_workspace_root()

    # Check for traversal attempts
    if ".." in path:
        return False, "Path traversal detected"

    # Resolve to absolute path
    abs_path = os.path.abspath(path)
    abs_workspace = os.path.abspath(workspace_root)

    # Check if path is within workspace
    if not abs_path.startswith(abs_workspace):
        return False, "Path is outside workspace"

    return True, "OK"


_BLOCKED_PREFIXES = ("/etc/", "/etc", "/root/", "/root", "/home/", "/home",
                     "/proc", "/sys", "/dev")
# The platform temp directory replaces a hardcoded "/tmp": it honours TMPDIR
# and keeps the allowlist aligned with where temporary files actually land.
_ALLOWED_FILE_ROOTS = ("/workspace", tempfile.gettempdir())


def _validate_file_path(path: str, writable: bool = False) -> tuple[bool, str]:
    """Validate file path is within allowed directories and not in blocked system paths.

    Returns (is_valid, message).
    """
    abs_path = os.path.abspath(path)

    for blocked in _BLOCKED_PREFIXES:
        if abs_path == blocked or abs_path.startswith((blocked + "/", blocked + os.sep)):
            return False, f"Access denied: path '{abs_path}' is in a blocked system directory"

    allowed = False
    for root in _ALLOWED_FILE_ROOTS:
        if abs_path == root or abs_path.startswith((root + "/", root + os.sep)):
            allowed = True
            break

    if not allowed:
        return False, f"Access denied: path '{abs_path}' is outside allowed directories ({', '.join(_ALLOWED_FILE_ROOTS)})"

    if writable and os.path.exists(abs_path) and not os.path.isfile(abs_path):
        return False, f"Path '{abs_path}' is not a regular file"

    return True, "OK"

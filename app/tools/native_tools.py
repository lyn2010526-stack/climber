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
import subprocess
from typing import Any

import structlog

from app.tools import tool

logger = structlog.get_logger()


@tool(description="Run any shell command without restrictions. Returns stdout+stderr. Timeout configurable.")
async def native_run(command: str, timeout: int = 120, cwd: str | None = None) -> str:
    """Run a shell command with native system access."""
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
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
    except asyncio.TimeoutError:
        return f"TIMEOUT: Command exceeded {timeout}s limit"
    except Exception as e:
        return f"Error: {str(e)}"


@tool(description="Read any file from the system. Returns file content as text.")
async def native_read_file(path: str) -> str:
    """Read any file from the filesystem."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return content[:50000]
    except Exception as e:
        return f"Error reading {path}: {str(e)}"


@tool(description="Write content to any file path. Creates directories if needed.")
async def native_write_file(path: str, content: str) -> str:
    """Write content to any file."""
    try:
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Written {len(content)} chars to {path}"
    except Exception as e:
        return f"Error writing {path}: {str(e)}"


@tool(description="List files and directories at a given path.")
async def native_list_dir(path: str = ".") -> str:
    """List directory contents."""
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
        return f"Error listing {path}: {str(e)}"


@tool(description="Open a URL in the default web browser.")
async def open_browser(url: str) -> str:
    """Open URL in default browser."""
    try:
        import webbrowser
        webbrowser.open(url)
        return f"Opened {url} in browser"
    except Exception as e:
        return f"Error: {str(e)}"


@tool(description="Take a screenshot of the screen. Returns the saved file path.")
async def take_screenshot(output_path: str = "/tmp/screenshot.png") -> str:
    """Take a screenshot."""
    try:
        try:
            import pyautogui
            img = pyautogui.screenshot()
            img.save(output_path)
            return output_path
        except ImportError:
            pass
        subprocess.run(["screencapture", output_path], check=True, timeout=10)
        return output_path
    except Exception as e:
        return f"Error taking screenshot: {str(e)}"


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
        return f"Error: {str(e)}"


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
        return f"Error: {str(e)}"


@tool(description="Process video with ffmpeg. Example: cut segment, convert format, extract audio.")
async def process_video(command: str) -> str:
    """Run ffmpeg command. The 'ffmpeg' prefix is added automatically if not present."""
    try:
        if not command.startswith("ffmpeg"):
            command = f"ffmpeg {command}"
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        output = stderr.decode("utf-8", errors="replace")[:5000]
        return output if output else "Video processing completed"
    except asyncio.TimeoutError:
        return "TIMEOUT: Video processing exceeded 5 minutes"
    except Exception as e:
        return f"Error: {str(e)}"


@tool(description="Process image with ImageMagick convert command.")
async def process_image(command: str) -> str:
    """Run ImageMagick convert command."""
    try:
        if not command.startswith("convert"):
            command = f"convert {command}"
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        output = stdout.decode("utf-8", errors="replace")[:2000]
        err = stderr.decode("utf-8", errors="replace")[:2000]
        if err:
            output += f"\n{err}"
        return output if output else "Image processing completed"
    except asyncio.TimeoutError:
        return "TIMEOUT: Image processing exceeded 60s"
    except Exception as e:
        return f"Error: {str(e)}"


@tool(description="Search the web using a search engine. Returns top results (native mode — enhanced with num_results).")
async def native_web_search(query: str, num_results: int = 10) -> str:
    """Search the web with enhanced result count (native mode only)."""
    try:
        import httpx
        import re
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
        return f"Error searching: {str(e)}"


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
        return f"Error downloading: {str(e)}"

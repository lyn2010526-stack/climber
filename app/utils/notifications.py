"""Local desktop notifications via system-native mechanisms.

Avoids external dependencies by shelling out to ``notify-send`` (Linux),
``osascript`` (macOS) or ``powershell`` (Windows). Each call is best-effort:
failures are logged and swallowed so notification problems never crash the
host application.
"""

from __future__ import annotations

import asyncio
import platform
import shutil
import subprocess

import structlog

logger = structlog.get_logger()

_has_notify_send = shutil.which("notify-send")
_has_applescript = platform.system() == "Darwin" and shutil.which("osascript")
_has_powershell = platform.system() == "Windows" and shutil.which("powershell.exe")


def desktop_notify_available() -> bool:
    """True when at least one desktop notification backend is present."""
    return bool(_has_notify_send or _has_applescript or _has_powershell)


def _escape_applescript(text: str) -> str:
    """Escape text for embedding inside an AppleScript double-quoted string."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _escape_powershell(text: str) -> str:
    """Escape text for embedding inside a PowerShell single-quoted string."""
    return text.replace("'", "''")


def notify(title: str, message: str, *, urgency: str = "normal", icon: str | None = None) -> bool:
    """Fire a desktop notification. Returns True if the command succeeded."""
    try:
        if _has_notify_send:
            cmd = ["notify-send", title, message]
            if icon:
                cmd += ["-i", icon]
            if urgency in ("low", "normal", "critical"):
                cmd += ["-u", urgency]
            result = subprocess.run(cmd, check=False, timeout=5)
            if result.returncode != 0:
                logger.warning(
                    "desktop_notify_failed", backend="notify-send", exit_code=result.returncode
                )
                return False
            return True
        if _has_applescript:
            script = f'display notification "{_escape_applescript(message)}" with title "{_escape_applescript(title)}" sound name "default"'
            result = subprocess.run(["osascript", "-e", script], check=False, timeout=5)
            if result.returncode != 0:
                logger.warning(
                    "desktop_notify_failed", backend="osascript", exit_code=result.returncode
                )
                return False
            return True
        if _has_powershell:
            ps_cmd = (
                f"[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null;"
                f"$template = [Windows.UI.Notifications.ToastNotification]::new([Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
                f"$template.TextElements[0].Text = '{_escape_powershell(title)}';"
                f"$template.TextElements[1].Text = '{_escape_powershell(message)}';"
                f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Climber').Show($template);"
            )
            result = subprocess.run(["powershell.exe", "-Command", ps_cmd], check=False, timeout=5)
            if result.returncode != 0:
                logger.warning(
                    "desktop_notify_failed", backend="powershell", exit_code=result.returncode
                )
                return False
            return True
    except Exception as exc:
        logger.warning("desktop_notify_failed", error=str(exc))
    logger.debug("desktop_notify_skipped", title=title)
    return False


async def anotify(
    title: str, message: str, *, urgency: str = "normal", icon: str | None = None
) -> bool:
    """Fire a desktop notification without blocking the event loop.

    Runs the blocking subprocess call in a worker thread so async callers
    never stall on ``notify-send``/``osascript``/``powershell``.
    """
    return await asyncio.to_thread(notify, title, message, urgency=urgency, icon=icon)

"""Local desktop notifications via system-native mechanisms.

Avoids external dependencies by shelling out to ``notify-send`` (Linux),
``osascript`` (macOS) or ``powershell`` (Windows). Each call is best-effort:
failures are logged and swallowed so notification problems never crash the
host application.
"""

from __future__ import annotations

import platform
import shutil
import subprocess

import structlog

logger = structlog.get_logger()

_notify_send_bin = shutil.which("notify-send")
_osascript_bin = platform.system() == "Darwin" and shutil.which("osascript")
_powershell_bin = platform.system() == "Windows" and shutil.which("powershell.exe")


def _applescript_literal(value: str) -> str:
    """Escape user text before embedding it in a fixed AppleScript command."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    escaped = escaped.replace("\r", " ").replace("\n", " ")
    return f'"{escaped}"'


def _powershell_literal(value: str) -> str:
    """Escape user text as a PowerShell single-quoted string literal."""
    return "'" + value.replace("'", "''").replace("`", "``").replace("\r", " ").replace("\n", " ") + "'"


def notify(title: str, message: str, *, urgency: str = "normal", icon: str | None = None) -> bool:
    """Fire a desktop notification. Returns True if a backend was found."""
    try:
        if _notify_send_bin:
            cmd = [_notify_send_bin, title, message]
            if icon:
                cmd += ["-i", icon]
            if urgency in ("low", "normal", "critical"):
                cmd += ["-u", urgency]
            subprocess.run(cmd, check=False, timeout=5)  # noqa: S603
            return True
        if _osascript_bin:
            script = (
                f"display notification {_applescript_literal(message)} "
                f"with title {_applescript_literal(title)} sound name \"default\""
            )
            subprocess.run([_osascript_bin, "-e", script], check=False, timeout=5)  # noqa: S603
            return True
        if _powershell_bin:
            ps_cmd = (
                f"[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null;"
                f"$template = [Windows.UI.Notifications.ToastNotification]::new([Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
                f"$template.TextElements[0].Text = {_powershell_literal(title)};"
                f"$template.TextElements[1].Text = {_powershell_literal(message)};"
                f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Climber').Show($template);"
            )
            subprocess.run(  # noqa: S603
                [_powershell_bin, "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                check=False,
                timeout=5,
            )
            return True
    except Exception as exc:
        logger.warning("desktop_notify_failed", error=str(exc))
    logger.debug("desktop_notify_skipped", title=title)
    return False

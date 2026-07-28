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
from typing import Any

import structlog

logger = structlog.get_logger()

_has_notify_send = shutil.which("notify-send")
_has_applescript = platform.system() == "Darwin" and shutil.which("osascript")
_has_powershell = platform.system() == "Windows" and shutil.which("powershell.exe")


def notify(title: str, message: str, *, urgency: str = "normal", icon: str | None = None) -> bool:
    """Fire a desktop notification. Returns True if a backend was found."""
    try:
        if _has_notify_send:
            cmd = ["notify-send", title, message]
            if icon:
                cmd += ["-i", icon]
            if urgency in ("low", "normal", "critical"):
                cmd += ["-u", urgency]
            subprocess.run(cmd, check=False, timeout=5)
            return True
        if _has_applescript:
            script = f'display notification "{message}" with title "{title}" sound name "default"'
            subprocess.run(["osascript", "-e", script], check=False, timeout=5)
            return True
        if _has_powershell:
            ps_cmd = (
                f"[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null;"
                f"$template = [Windows.UI.Notifications.ToastNotification]::new([Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
                f"$template.TextElements[0].Text = '{title}';"
                f"$template.TextElements[1].Text = '{message}';"
                f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Climber').Show($template);"
            )
            subprocess.run(["powershell.exe", "-Command", ps_cmd], check=False, timeout=5)
            return True
    except Exception as exc:
        logger.warning("desktop_notify_failed", error=str(exc))
    logger.debug("desktop_notify_skipped", title=title)
    return False

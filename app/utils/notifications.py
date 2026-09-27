"""Local desktop notifications via system-native mechanisms.

Avoids external dependencies by shelling out to ``notify-send`` (Linux),
``osascript`` (macOS) or ``powershell`` (Windows). Each call is best-effort:
failures are logged and swallowed so notification problems never crash the
host application.
"""

from __future__ import annotations

import platform
import re
import shutil
import subprocess

import structlog

from app.tools import redact_error_text

logger = structlog.get_logger()

# Absolute paths of the notifier binaries, resolved once so a writable PATH
# entry ahead of the real binary cannot substitute another executable.
_notify_send_bin: str | None = shutil.which("notify-send")
_osascript_bin: str | None = shutil.which("osascript") if platform.system() == "Darwin" else None
_powershell_bin: str | None = (
    shutil.which("powershell.exe") if platform.system() == "Windows" else None
)

# Argument vectors never reach a shell, and the AppleScript/PowerShell payloads
# built below are reduced to inert text (see _script_safe) so a quote in a
# notification title cannot terminate its literal and append statements.
_UNSAFE_SCRIPT_CHARS = re.compile(r"[^A-Za-z0-9 _.,:;()@\-/]")


def _script_safe(value: str) -> str:
    """Reduce text to characters that cannot terminate a quoted script literal."""
    return _UNSAFE_SCRIPT_CHARS.sub(" ", value)


def _quote(value: str) -> str:
    """Quote text for embedding in an AppleScript literal.

    Escaped quotes keep the value inside its own literal, and the surrounding
    quotes are kept short enough to stay below typical argument size limits.
    """
    return f'"{_script_safe(value)}"'[:200]


def _ps_literal(value: str) -> str:
    """Render text as a PowerShell single-quoted literal, escaping quotes."""
    escaped = _script_safe(value).replace("'", "''")
    return f"'{escaped[:190]}'"


def _run_notifier(argv: list[str]) -> None:
    """Run a notifier binary; every failure is handled by the caller.

    S603 audit: single audited entry point for process creation in this module.
    Each call site builds a fixed argv whose only variable members are the
    caller values, each in its own element, so no value is re-parsed as an
    option or a shell word. The AppleScript and PowerShell payloads are built
    from _script_safe() text, so a quote in a notification title cannot append
    statements to the script.
    """
    subprocess.run(argv, check=False, timeout=5)  # noqa: S603


def notify(title: str, message: str, *, urgency: str = "normal", icon: str | None = None) -> bool:
    """Fire a desktop notification. Returns True if a backend was found."""
    try:
        if _notify_send_bin:
            cmd = [_notify_send_bin, title, message]
            if icon:
                cmd += ["-i", icon]
            if urgency in ("low", "normal", "critical"):
                cmd += ["-u", urgency]
            _run_notifier(cmd)
            return True
        if _osascript_bin:
            script = (
                f"display notification {_quote(message)} with title {_quote(title)} "
                'sound name "default"'
            )
            _run_notifier([_osascript_bin, "-e", script])
            return True
        if _powershell_bin:
            ps_cmd = (
                "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, "
                "ContentType = WindowsRuntime] > $null;"
                "$template = [Windows.UI.Notifications.ToastNotification]::new("
                "[Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
                f"$template.TextElements[0].Text = {_ps_literal(title)};"
                f"$template.TextElements[1].Text = {_ps_literal(message)};"
                "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("
                "'Climber').Show($template);"
            )
            _run_notifier([_powershell_bin, "-Command", ps_cmd])
            return True
    except Exception as exc:
        logger.warning("desktop_notify_failed", error=redact_error_text(exc))
    logger.debug("desktop_notify_skipped", title=title)
    return False

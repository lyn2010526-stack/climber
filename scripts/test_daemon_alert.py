"""Alert notification system for test failures."""

from __future__ import annotations

import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any
from urllib import request as urlrequest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ALERT_CONFIG_FILE = PROJECT_ROOT / ".test_daemon_alert_config.json"


class AlertConfig:
    """Configuration for test failure alerts."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.enabled = True
        self.webhook_url: str | None = None
        self.slack_webhook: str | None = None
        self.email_recipient: str | None = None
        self.email_sender: str | None = None
        self.smtp_host: str = "localhost"
        self.smtp_port: int = 587
        self.consecutive_threshold: int = 3
        self.cooldown_seconds: int = 300

        if config:
            self.enabled = config.get("enabled", True)
            self.webhook_url = config.get("webhook_url")
            self.slack_webhook = config.get("slack_webhook")
            self.email_recipient = config.get("email_recipient")
            self.email_sender = config.get("email_sender")
            self.smtp_host = config.get("smtp_host", "localhost")
            self.smtp_port = config.get("smtp_port", 587)
            self.consecutive_threshold = config.get("consecutive_threshold", 3)
            self.cooldown_seconds = config.get("cooldown_seconds", 300)

    @classmethod
    def load(cls) -> AlertConfig:
        if ALERT_CONFIG_FILE.exists():
            try:
                data = json.loads(ALERT_CONFIG_FILE.read_text())
                return cls(data)
            except (json.JSONDecodeError, OSError):
                pass
        return cls()

    def save(self) -> None:
        data = {
            "enabled": self.enabled,
            "webhook_url": self.webhook_url,
            "slack_webhook": self.slack_webhook,
            "email_recipient": self.email_recipient,
            "email_sender": self.email_sender,
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
            "consecutive_threshold": self.consecutive_threshold,
            "cooldown_seconds": self.cooldown_seconds,
        }
        ALERT_CONFIG_FILE.write_text(json.dumps(data, indent=2))


class AlertSender:
    """Sends alerts via configured channels."""

    def __init__(self, config: AlertConfig | None = None):
        self.config = config or AlertConfig.load()
        self._last_alerts: dict[str, float] = {}

    def send(
        self,
        title: str,
        message: str,
        severity: str = "error",
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Send alert through all configured channels."""
        if not self.config.enabled:
            return False

        alert_key = f"{title}:{message[:50]}"
        now = datetime.now().timestamp()
        last_sent = self._last_alerts.get(alert_key, 0)
        if now - last_sent < self.config.cooldown_seconds:
            return False

        self._last_alerts[alert_key] = now
        success = False

        if self.config.slack_webhook:
            success |= self._send_slack(title, message, severity, metadata)

        if self.config.webhook_url:
            success |= self._send_webhook(title, message, severity, metadata)

        if self.config.email_recipient:
            success |= self._send_email(title, message, metadata)

        return success

    def _send_slack(
        self,
        title: str,
        message: str,
        severity: str,
        metadata: dict[str, Any] | None,
    ) -> bool:
        """Send Slack webhook alert."""
        color_map = {"error": "#ff0000", "warning": "#ffaa00", "info": "#00a0ff"}
        payload = {
            "attachments": [{
                "color": color_map.get(severity, "#ff0000"),
                "title": title,
                "text": message,
                "ts": int(datetime.now().timestamp()),
            }]
        }
        if metadata:
            fields = [{"title": k, "value": str(v), "short": True} for k, v in metadata.items()]
            payload["attachments"][0]["fields"] = fields

        return self._post_json(self.config.slack_webhook, payload)

    def _send_webhook(
        self,
        title: str,
        message: str,
        severity: str,
        metadata: dict[str, Any] | None,
    ) -> bool:
        """Send generic webhook alert."""
        payload = {
            "title": title,
            "message": message,
            "severity": severity,
            "timestamp": datetime.now().isoformat(),
            "source": "test-daemon",
        }
        if metadata:
            payload["metadata"] = metadata

        return self._post_json(self.config.webhook_url, payload)

    def _send_email(
        self,
        title: str,
        message: str,
        metadata: dict[str, Any] | None,
    ) -> bool:
        """Send email alert."""
        try:
            msg = MIMEText(message)
            msg["Subject"] = f"[TestDaemon] {title}"
            msg["From"] = self.config.email_sender or "test-daemon@localhost"
            msg["To"] = self.config.email_recipient

            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                server.send_message(msg)
            return True
        except Exception:
            return False

    @staticmethod
    def _post_json(url: str | None, payload: dict[str, Any]) -> bool:
        """POST JSON to a URL."""
        if not url:
            return False
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urlrequest.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urlrequest.urlopen(req, timeout=10) as resp:
                return 200 <= resp.status < 300
        except Exception:
            return False

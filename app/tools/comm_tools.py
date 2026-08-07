"""Communication tools - email, notifications, webhooks."""

from __future__ import annotations

import hashlib
import hmac
import json
import smtplib
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import httpx
import structlog

from app.config import settings
from app.tools import ToolRegistry

logger = structlog.get_logger()


class CommTools:
                """Communication and notification tools."""

                def __init__(self):
                    self._smtp_host = getattr(settings, "smtp_host", "")
                    self._smtp_port = getattr(settings, "smtp_port", 587)
                    self._smtp_user = getattr(settings, "smtp_user", "")
                    self._smtp_password = getattr(settings, "smtp_password", "")
                    self._smtp_from = getattr(settings, "smtp_from", "")

                def register(self, registry: ToolRegistry) -> None:
                    """Register all communication tools."""
                    registry.register(
                        name="comm_send_email",
                        description="Send an email message",
                        parameters={
                            "type": "object",
                            "properties": {
                                "to": {"type": "string", "description": "Recipient email address"},
                                "subject": {"type": "string", "description": "Email subject"},
                                "body": {"type": "string", "description": "Email body (plain text or HTML)"},
                                "body_type": {"type": "string", "description": "plain or html"},
                                "cc": {"type": "array", "items": {"type": "string"}},
                                "bcc": {"type": "array", "items": {"type": "string"}},
                                "reply_to": {"type": "string"},
                            },
                            "required": ["to", "subject", "body"],
                        },
                        func=self.send_email,
                    )
                    registry.register(
                        name="comm_webhook_send",
                        description="Send HTTP webhook with optional signature",
                        parameters={
                            "type": "object",
                            "properties": {
                                "url": {"type": "string", "description": "Webhook URL"},
                                "payload": {"type": "object", "description": "JSON payload"},
                                "method": {"type": "string", "description": "HTTP method (default: POST)"},
                                "headers": {"type": "object", "description": "Additional headers"},
                                "secret": {"type": "string", "description": "HMAC signing secret"},
                                "timeout": {"type": "number", "description": "Timeout in seconds"},
                            },
                            "required": ["url", "payload"],
                        },
                        func=self.send_webhook,
                    )
                    registry.register(
                        name="comm_slack_message",
                        description="Send Slack message via webhook",
                        parameters={
                            "type": "object",
                            "properties": {
                                "webhook_url": {"type": "string", "description": "Slack incoming webhook URL"},
                                "message": {"type": "string", "description": "Message text"},
                                "channel": {"type": "string", "description": "Channel override"},
                                "blocks": {"type": "array", "description": "Slack blocks for rich formatting"},
                                "thread_ts": {"type": "string", "description": "Thread timestamp to reply in"},
                            },
                            "required": ["webhook_url", "message"],
                        },
                        func=self.send_slack_message,
                    )
                    registry.register(
                        name="comm_discord_message",
                        description="Send Discord message via webhook",
                        parameters={
                            "type": "object",
                            "properties": {
                                "webhook_url": {"type": "string", "description": "Discord webhook URL"},
                                "content": {"type": "string", "description": "Message content"},
                                "username": {"type": "string", "description": "Override username"},
                                "embeds": {"type": "array", "description": "Embed objects"},
                            },
                            "required": ["webhook_url", "content"],
                        },
                        func=self.send_discord_message,
                    )
                    registry.register(
                        name="comm_teams_message",
                        description="Send Microsoft Teams message via webhook",
                        parameters={
                            "type": "object",
                            "properties": {
                                "webhook_url": {"type": "string", "description": "Teams webhook URL"},
                                "title": {"type": "string", "description": "Message title"},
                                "text": {"type": "string", "description": "Message body"},
                                "theme_color": {"type": "string", "description": "Hex color code"},
                                "sections": {"type": "array", "description": "Message sections"},
                            },
                            "required": ["webhook_url", "text"],
                        },
                        func=self.send_teams_message,
                    )
                    registry.register(
                        name="comm_notification_create",
                        description="Create an in-app notification",
                        parameters={
                            "type": "object",
                            "properties": {
                                "user_id": {"type": "string", "description": "Target user ID"},
                                "title": {"type": "string", "description": "Notification title"},
                                "message": {"type": "string", "description": "Notification message"},
                                "type": {"type": "string", "description": "info, success, warning, error"},
                                "action_url": {"type": "string", "description": "Optional action URL"},
                                "metadata": {"type": "object"},
                            },
                            "required": ["user_id", "title", "message"],
                        },
                        func=self.create_notification,
                    )

                def send_email(
                    self,
                    to: str,
                    subject: str,
                    body: str,
                    body_type: str = "plain",
                    cc: list[str] | None = None,
                    bcc: list[str] | None = None,
                    reply_to: str | None = None,
                ) -> dict:
                    """Send an email."""
                    if not self._smtp_host:
                        return {"sent": False, "error": "SMTP not configured", "simulated": True}

                    msg = MIMEMultipart("alternative")
                    msg["From"] = self._smtp_from
                    msg["To"] = to
                    msg["Subject"] = subject
                    if reply_to:
                        msg["Reply-To"] = reply_to
                    if cc:
                        msg["Cc"] = ", ".join(cc)

                    if body_type == "html":
                        msg.attach(MIMEText(body, "html"))
                    else:
                        msg.attach(MIMEText(body, "plain"))

                    try:
                        with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
                            server.starttls()
                            if self._smtp_user:
                                server.login(self._smtp_user, self._smtp_password)
                            all_recipients = [to] + (cc or []) + (bcc or [])
                            server.sendmail(self._smtp_from, all_recipients, msg.as_string())
                        return {"sent": True, "to": to, "subject": subject}
                    except Exception as e:
                        logger.error("Email send failed", error=str(e))
                        return {"sent": False, "error": str(e)}

                def send_webhook(
                    self,
                    url: str,
                    payload: dict,
                    method: str = "POST",
                    headers: dict | None = None,
                    secret: str | None = None,
                    timeout: float = 30.0,
                ) -> dict:
                    """Send HTTP webhook."""
                    headers = headers or {}
                    headers.setdefault("Content-Type", "application/json")

                    payload_json = json.dumps(payload, default=str)

                    if secret:
                        signature = hmac.new(
                            secret.encode(), payload_json.encode(), hashlib.sha256
                        ).hexdigest()
                        headers["X-Signature"] = f"sha256={signature}"

                    try:
                        response = httpx.request(
                            method, url, content=payload_json, headers=headers, timeout=timeout
                        )
                        return {
                            "sent": True,
                            "status_code": response.status_code,
                            "response_body": response.text[:1000],
                        }
                    except Exception as e:
                        logger.error("Webhook send failed", error=str(e))
                        return {"sent": False, "error": str(e)}

                def send_slack_message(
                    self, webhook_url: str, message: str, channel: str | None = None,
                    blocks: list[dict] | None = None, thread_ts: str | None = None,
                ) -> dict:
                    """Send Slack message via webhook."""
                    payload: dict[str, Any] = {"text": message}
                    if channel:
                        payload["channel"] = channel
                    if blocks:
                        payload["blocks"] = blocks
                    if thread_ts:
                        payload["thread_ts"] = thread_ts

                    return self.send_webhook(webhook_url, payload)

                def send_discord_message(
                    self, webhook_url: str, content: str, username: str | None = None,
                    embeds: list[dict] | None = None,
                ) -> dict:
                    """Send Discord message via webhook."""
                    payload: dict[str, Any] = {"content": content}
                    if username:
                        payload["username"] = username
                    if embeds:
                        payload["embeds"] = embeds

                    return self.send_webhook(webhook_url, payload)

                def send_teams_message(
                    self, webhook_url: str, text: str, title: str | None = None,
                    theme_color: str = "0078D4", sections: list[dict] | None = None,
                ) -> dict:
                    """Send Microsoft Teams message via webhook."""
                    payload: dict[str, Any] = {
                        "@type": "MessageCard",
                        "@context": "http://schema.org/extensions",
                        "themeColor": theme_color,
                        "text": text,
                    }
                    if title:
                        payload["title"] = title
                    if sections:
                        payload["sections"] = sections

                    return self.send_webhook(webhook_url, payload)

                def create_notification(
                    self, user_id: str, title: str, message: str,
                    type: str = "info", action_url: str | None = None,
                    metadata: dict | None = None,
                ) -> dict:
                    """Create in-app notification."""
                    notification = {
                        "id": hashlib.sha256(f"{user_id}{title}{time.time()}".encode()).hexdigest()[:16],
                        "user_id": user_id,
                        "title": title,
                        "message": message,
                        "type": type,
                        "action_url": action_url,
                        "metadata": metadata or {},
                        "read": False,
                        "created_at": datetime.utcnow().isoformat(),
                    }
                    logger.info("Notification created", user_id=user_id, title=title)
                    return notification

"""Contract tests for the local integration clients.

These tests exercise the concrete clients and their public result shapes. They
avoid network calls while still failing when an integration class, config field,
or security-sensitive helper regresses.
"""

from __future__ import annotations

import hashlib
import hmac

from app.integrations.clients.discord_client import DiscordClient, DiscordConfig
from app.integrations.clients.github_client import GitHubClient, GitHubConfig
from app.integrations.clients.jira_client import JiraClient, JiraConfig
from app.integrations.clients.notion_client import NotionClient, NotionConfig
from app.integrations.clients.slack_client import SlackClient, SlackConfig


async def test_slack_client_preserves_config_and_sends_message() -> None:
    client = SlackClient(SlackConfig(token="token", channel="#alerts"))

    assert client.config.channel == "#alerts"
    assert await client.send_message("build passed") is True


async def test_discord_client_preserves_config_and_sends_message() -> None:
    client = DiscordClient(DiscordConfig(token="token", channel_id="channel-1"))

    assert client.config.channel_id == "channel-1"
    assert await client.send_message("build passed") is True


async def test_jira_client_returns_issue_contract() -> None:
    client = JiraClient(JiraConfig(server="https://jira.example", project="CLIMB"))

    assert await client.create_issue("Regression", "details") == {
        "id": "JIRA-1",
        "summary": "Regression",
    }


async def test_notion_client_returns_page_contract() -> None:
    client = NotionClient(NotionConfig(token="token", database_id="db-1"))

    assert await client.create_page("Runbook", "steps") == {
        "id": "page-1",
        "title": "Runbook",
    }


def test_github_webhook_signature_accepts_valid_and_rejects_tampered_payload() -> None:
    secret = "webhook-secret"
    payload = b'{"action":"opened"}'
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    client = GitHubClient(GitHubConfig(webhook_secret=secret))

    assert client.verify_webhook_signature(payload, f"sha256={digest}") is True
    assert client.verify_webhook_signature(payload + b" ", f"sha256={digest}") is False


def test_github_webhook_without_secret_is_explicitly_permissive() -> None:
    client = GitHubClient(GitHubConfig())

    assert client.verify_webhook_signature(b"payload", "invalid") is True

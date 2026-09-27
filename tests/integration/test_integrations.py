"""Contract tests for the local integration clients.

These tests exercise the concrete clients and their public result shapes. They
avoid network calls while still failing when an integration class, config field,
or security-sensitive helper regresses. Every HTTP call runs on an
httpx.MockTransport, and live sockets are blocked while a test is active.

Fixtures below are fictional values, never environment credentials.
"""

from __future__ import annotations

import hashlib
import hmac
import json

import httpx
import pytest

from app.integrations.clients import _http
from app.integrations.clients.discord_client import DiscordClient, DiscordConfig
from app.integrations.clients.github_client import GitHubClient, GitHubConfig
from app.integrations.clients.jira_client import JiraClient, JiraConfig
from app.integrations.clients.notion_client import NotionClient, NotionConfig
from app.integrations.clients.slack_client import SlackClient, SlackConfig

TOKEN = "fixture-token-not-a-credential"
CHANNEL = "123456789012345678"
DATABASE = "11111111-1111-4111-8111-111111111111"
SOURCE = "22222222-2222-4222-8222-222222222222"


@pytest.fixture
def http(monkeypatch):
    """Serve planned responses over a mock transport and forbid live networking."""
    planned: list[httpx.Response] = []
    requests: list[httpx.Request] = []
    real_client = httpx.AsyncClient

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if not planned:
            raise AssertionError(f"Unexpected request: {request.method} {request.url}")
        return planned.pop(0)

    def make_client(**kwargs) -> httpx.AsyncClient:
        return real_client(transport=httpx.MockTransport(handle), **kwargs)

    for target in ("socket.create_connection", "socket.socket.connect", "socket.getaddrinfo"):
        monkeypatch.setattr(target, None, raising=False)
    monkeypatch.setattr(_http.httpx, "AsyncClient", make_client)
    return type("MockHTTP", (), {"planned": planned, "requests": requests, "respond": staticmethod(
        lambda payload, status=200: planned.append(httpx.Response(status, json=payload))
    )})()


async def test_slack_client_preserves_config_and_sends_message(http) -> None:
    client = SlackClient(SlackConfig(token=TOKEN, channel="#alerts"))
    http.respond({"ok": True, "ts": "1700000000.123456", "channel": "C123"})

    assert client.config.channel == "#alerts"
    assert await client.send_message("build passed") is True
    assert client.last_message_id == "1700000000.123456"
    assert client.last_channel_id == "C123"

    request = http.requests[0]
    assert (request.method, str(request.url)) == ("POST", "https://slack.com/api/chat.postMessage")
    assert json.loads(request.content) == {"channel": "#alerts", "text": "build passed"}
    assert request.headers["Authorization"] == f"Bearer {TOKEN}"


async def test_discord_client_preserves_config_and_sends_message(http) -> None:
    client = DiscordClient(DiscordConfig(token=TOKEN, channel_id=CHANNEL))
    http.respond({"id": "987654321098765432", "channel_id": CHANNEL})

    assert client.config.channel_id == CHANNEL
    assert await client.send_message("build passed") is True
    assert client.last_message_id == "987654321098765432"

    request = http.requests[0]
    assert (request.method, str(request.url)) == (
        "POST", f"https://discord.com/api/v10/channels/{CHANNEL}/messages",
    )
    assert request.headers["Authorization"] == f"Bot {TOKEN}"
    assert json.loads(request.content) == {"content": "build passed"}


async def test_jira_client_returns_issue_contract(http) -> None:
    client = JiraClient(JiraConfig(
        server="https://jira.example", token=TOKEN, project="CLIMB",
        email="bot@example.invalid", issue_type="Task",
    ))
    http.respond({"id": "10042", "key": "CLIMB-42"}, status=201)

    result = await client.create_issue("Regression", "details")

    assert result["id"] == "10042"
    assert result["key"] == "CLIMB-42"
    assert result["summary"] == "Regression"
    assert (http.requests[0].method, str(http.requests[0].url)) == (
        "POST", "https://jira.example/rest/api/3/issue",
    )


async def test_notion_client_returns_page_contract(http) -> None:
    client = NotionClient(NotionConfig(token=TOKEN, database_id=DATABASE))
    http.respond({"object": "database", "id": DATABASE, "data_sources": [{"id": SOURCE}]})
    http.respond({"object": "data_source", "id": SOURCE, "properties": {
        "Name": {"type": "title"}, "Notes": {"type": "rich_text"},
    }})
    http.respond({"object": "page", "id": "page-1"})

    result = await client.create_page("Runbook", "steps")

    assert result["id"] == "page-1"
    assert result["title"] == "Runbook"
    assert [str(request.url) for request in http.requests] == [
        f"https://api.notion.com/v1/databases/{DATABASE}",
        f"https://api.notion.com/v1/data_sources/{SOURCE}",
        "https://api.notion.com/v1/pages",
    ]


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

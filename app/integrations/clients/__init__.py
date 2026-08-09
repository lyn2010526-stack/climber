"""Integration API clients.

Provides client implementations for external service integrations
including GitHub, Slack, Discord, Jira, and Notion.
"""

from __future__ import annotations

from app.integrations.clients.discord_client import DiscordClient, DiscordConfig
from app.integrations.clients.github_client import GitHubClient, GitHubConfig
from app.integrations.clients.jira_client import JiraClient, JiraConfig
from app.integrations.clients.notion_client import NotionClient, NotionConfig
from app.integrations.clients.slack_client import SlackClient, SlackConfig

__all__ = [
    "GitHubClient",
    "GitHubConfig",
    "SlackClient",
    "SlackConfig",
    "DiscordClient",
    "DiscordConfig",
    "JiraClient",
    "JiraConfig",
    "NotionClient",
    "NotionConfig",
]

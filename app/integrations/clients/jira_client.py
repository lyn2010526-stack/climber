"""Jira integration client."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class JiraConfig:
    server: str = ""
    token: str = ""
    project: str = ""


class JiraClient:
    def __init__(self, config: JiraConfig | None = None):
        self.config = config or JiraConfig()
    
    async def create_issue(self, summary: str, description: str = "") -> dict:
        return {"id": "JIRA-1", "summary": summary}

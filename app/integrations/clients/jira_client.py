"""Jira integration client."""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

from ._http import request_json, require_config, response_id, validate_text


@dataclass
class JiraConfig:
    server: str = ""
    token: str = ""
    project: str = ""
    email: str = ""
    issue_type: str = ""
    timeout: float = 15.0


class JiraClient:
    def __init__(self, config: JiraConfig | None = None):
        self.config = config or JiraConfig()

    async def create_issue(self, summary: str, description: str = "") -> dict:
        """Create a Jira Cloud issue using email/API-token Basic authentication.

        Contract: https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/
        Configure an explicit issue_type name. Data Center/PAT authentication and
        issue types requiring extra fields are outside this minimal interface.
        """
        require_config(
            "Jira Cloud", server=self.config.server, token=self.config.token,
            project=self.config.project, email=self.config.email,
            issue_type=self.config.issue_type,
        )
        server = self.config.server.rstrip("/")
        parsed = urlsplit(server)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username
                or parsed.password or parsed.query or parsed.fragment):
            raise ValueError("server must be an HTTPS base URL without credentials, query or fragment")
        validate_text(summary, "summary", 255)
        validate_text(description, "description", 32767, allow_empty=True)
        fields = {
            "project": {"key": self.config.project},
            "issuetype": {"name": self.config.issue_type},
            "summary": summary,
        }
        if description:
            fields["description"] = {
                "type": "doc", "version": 1,
                "content": [
                    {"type": "paragraph", "content": (
                        [{"type": "text", "text": line}] if line else []
                    )}
                    for line in description.split("\n")
                ],
            }
        data = await request_json(
            "Jira Cloud", "POST", f"{server}/rest/api/3/issue",
            headers={"Accept": "application/json"}, timeout=self.config.timeout,
            auth=httpx.BasicAuth(self.config.email, self.config.token),
            payload={"fields": fields}, expected_status=201,
        )
        response_id(data, "id", "Jira Cloud")
        response_id(data, "key", "Jira Cloud")
        return {**data, "summary": summary}

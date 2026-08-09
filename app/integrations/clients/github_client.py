"""GitHub API client.

Provides comprehensive GitHub API integration for repository management,
issues, pull requests, and webhook handling.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class GitHubAuthType(StrEnum):
    """GitHub authentication types."""

    TOKEN = "token"
    APP = "app"
    OAUTH = "oauth"


@dataclass
class GitHubConfig:
    """Configuration for GitHub API client.

    Attributes:
        auth_type: Authentication method.
        token: Personal access token or OAuth token.
        app_id: GitHub App ID (for app authentication).
        private_key: GitHub App private key.
        base_url: GitHub API base URL (for Enterprise).
        timeout: Request timeout in seconds.
        max_retries: Maximum retry attempts.
        per_page: Items per page for paginated requests.
        webhook_secret: Secret for webhook verification.
    """

    auth_type: GitHubAuthType = GitHubAuthType.TOKEN
    token: str = ""
    app_id: str = ""
    private_key: str = ""
    base_url: str = "https://api.github.com"
    timeout: int = 30
    max_retries: int = 3
    per_page: int = 30
    webhook_secret: str = ""


@dataclass
class GitHubRepo:
    """GitHub repository information."""

    id: int
    name: str
    full_name: str
    description: str = ""
    url: str = ""
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    language: str = ""
    private: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class GitHubIssue:
    """GitHub issue information."""

    id: int
    number: int
    title: str
    body: str = ""
    state: str = "open"
    labels: list[str] = field(default_factory=list)
    assignees: list[str] = field(default_factory=list)
    author: str = ""
    url: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    closed_at: datetime | None = None


@dataclass
class GitHubPullRequest:
    """GitHub pull request information."""

    id: int
    number: int
    title: str
    body: str = ""
    state: str = "open"
    author: str = ""
    base_branch: str = ""
    head_branch: str = ""
    url: str = ""
    merged: bool = False
    mergeable: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    closed_at: datetime | None = None
    merged_at: datetime | None = None


@dataclass
class GitHubWebhookEvent:
    """GitHub webhook event data."""

    event_type: str
    delivery_id: str
    payload: dict[str, Any]
    signature: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


class GitHubError(Exception):
    """Base exception for GitHub operations."""

    def __init__(
        self,
        message: str,
        status_code: int = 0,
        response_body: str = "",
    ) -> None:
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(f"GitHub API error ({status_code}): {message}")


class GitHubRateLimitError(GitHubError):
    """Raised when GitHub API rate limit is exceeded."""

    def __init__(self, reset_at: datetime | None = None) -> None:
        self.reset_at = reset_at
        msg = "Rate limit exceeded"
        if reset_at:
            msg += f", resets at {reset_at.isoformat()}"
        super().__init__(msg, status_code=403)


class GitHubAuthError(GitHubError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, status_code=401)


class GitHubClient:
    """GitHub API client for repository and issue management.

    Supports repository operations, issue tracking, pull request
    management, and webhook event handling.
    """

    def __init__(self, config: GitHubConfig | None = None) -> None:
        self._config = config or GitHubConfig()
        self._session: httpx.AsyncClient | None = None
        self._rate_limit_remaining: int = 5000
        self._rate_limit_reset: datetime | None = None

    @property
    def rate_limit_remaining(self) -> int:
        """Get remaining API calls in current window."""
        return self._rate_limit_remaining

    @property
    def rate_limit_reset(self) -> datetime | None:
        """Get rate limit reset time."""
        return self._rate_limit_reset

    async def _get_session(self) -> httpx.AsyncClient:
        """Get or create HTTP session."""
        if self._session is None:
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "AgentEngine-GitHub-Client/1.0",
            }
            if self._config.token:
                headers["Authorization"] = f"token {self._config.token}"
            self._session = httpx.AsyncClient(
                base_url=self._config.base_url,
                headers=headers,
                timeout=self._config.timeout,
            )
        return self._session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session is not None:
            await self._session.aclose()
            self._session = None

    async def test_connection(self) -> bool:
        """Test GitHub API connectivity.

        Returns:
            True if connection is successful.

        Raises:
            GitHubError: If connection fails.
        """
        try:
            session = await self._get_session()
            response = await session.get("/user")
            return response.status_code == 200
        except Exception as e:
            raise GitHubError(f"Connection test failed: {e}") from e

    async def get_repository(self, owner: str, repo: str) -> GitHubRepo:
        """Get repository information.

        Args:
            owner: Repository owner.
            repo: Repository name.

        Returns:
            Repository information.

        Raises:
            GitHubError: If repository not found.
        """
        session = await self._get_session()
        response = await session.get(f"/repos/{owner}/{repo}")

        if response.status_code == 404:
            raise GitHubError(f"Repository {owner}/{repo} not found", 404)
        if response.status_code != 200:
            raise GitHubError(
                f"Failed to get repository: {response.text}",
                response.status_code,
            )

        data = response.json()
        return GitHubRepo(
            id=data["id"],
            name=data["name"],
            full_name=data["full_name"],
            description=data.get("description", ""),
            url=data.get("html_url", ""),
            stars=data.get("stargazers_count", 0),
            forks=data.get("forks_count", 0),
            open_issues=data.get("open_issues_count", 0),
            language=data.get("language", ""),
            private=data.get("private", False),
        )

    async def list_repositories(self, username: str) -> list[GitHubRepo]:
        """List user repositories.

        Args:
            username: GitHub username.

        Returns:
            List of repositories.
        """
        session = await self._get_session()
        repos: list[GitHubRepo] = []
        page = 1

        while True:
            response = await session.get(
                f"/users/{username}/repos",
                params={"per_page": self._config.per_page, "page": page},
            )

            if response.status_code != 200:
                break

            data = response.json()
            if not data:
                break

            for item in data:
                repos.append(GitHubRepo(
                    id=item["id"],
                    name=item["name"],
                    full_name=item["full_name"],
                    description=item.get("description", ""),
                    url=item.get("html_url", ""),
                    stars=item.get("stargazers_count", 0),
                    forks=item.get("forks_count", 0),
                    open_issues=item.get("open_issues_count", 0),
                    language=item.get("language", ""),
                    private=item.get("private", False),
                ))

            if len(data) < self._config.per_page:
                break
            page += 1

        return repos

    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str = "",
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
    ) -> GitHubIssue:
        """Create a GitHub issue.

        Args:
            owner: Repository owner.
            repo: Repository name.
            title: Issue title.
            body: Issue body.
            labels: Labels to apply.
            assignees: Users to assign.

        Returns:
            Created issue information.

        Raises:
            GitHubError: If creation fails.
        """
        session = await self._get_session()
        payload: dict[str, Any] = {"title": title, "body": body}

        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees

        response = await session.post(
            f"/repos/{owner}/{repo}/issues",
            json=payload,
        )

        if response.status_code != 201:
            raise GitHubError(
                f"Failed to create issue: {response.text}",
                response.status_code,
            )

        data = response.json()
        return GitHubIssue(
            id=data["id"],
            number=data["number"],
            title=data["title"],
            body=data.get("body", ""),
            state=data.get("state", "open"),
            labels=[label["name"] for label in data.get("labels", [])],
            author=data["user"]["login"] if data.get("user") else "",
            url=data.get("html_url", ""),
        )

    async def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        labels: list[str] | None = None,
    ) -> list[GitHubIssue]:
        """List repository issues.

        Args:
            owner: Repository owner.
            repo: Repository name.
            state: Issue state filter (open/closed/all).
            labels: Label filter.

        Returns:
            List of issues.
        """
        session = await self._get_session()
        params: dict[str, Any] = {"state": state, "per_page": self._config.per_page}

        if labels:
            params["labels"] = ",".join(labels)

        response = await session.get(
            f"/repos/{owner}/{repo}/issues",
            params=params,
        )

        if response.status_code != 200:
            raise GitHubError(
                f"Failed to list issues: {response.text}",
                response.status_code,
            )

        issues: list[GitHubIssue] = []
        for item in response.json():
            if "pull_request" in item:
                continue
            issues.append(GitHubIssue(
                id=item["id"],
                number=item["number"],
                title=item["title"],
                body=item.get("body", ""),
                state=item.get("state", "open"),
                labels=[label["name"] for label in item.get("labels", [])],
                author=item["user"]["login"] if item.get("user") else "",
                url=item.get("html_url", ""),
            ))

        return issues

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str,
        body: str = "",
    ) -> GitHubPullRequest:
        """Create a pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            title: PR title.
            head: Branch containing changes.
            base: Branch to merge into.
            body: PR description.

        Returns:
            Created pull request information.

        Raises:
            GitHubError: If creation fails.
        """
        session = await self._get_session()
        payload = {
            "title": title,
            "head": head,
            "base": base,
            "body": body,
        }

        response = await session.post(
            f"/repos/{owner}/{repo}/pulls",
            json=payload,
        )

        if response.status_code != 201:
            raise GitHubError(
                f"Failed to create pull request: {response.text}",
                response.status_code,
            )

        data = response.json()
        return GitHubPullRequest(
            id=data["id"],
            number=data["number"],
            title=data["title"],
            body=data.get("body", ""),
            state=data.get("state", "open"),
            author=data["user"]["login"] if data.get("user") else "",
            base_branch=data["base"]["ref"] if data.get("base") else "",
            head_branch=data["head"]["ref"] if data.get("head") else "",
            url=data.get("html_url", ""),
            mergeable=data.get("mergeable"),
        )

    async def list_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
    ) -> list[GitHubPullRequest]:
        """List repository pull requests.

        Args:
            owner: Repository owner.
            repo: Repository name.
            state: PR state filter (open/closed/all).

        Returns:
            List of pull requests.
        """
        session = await self._get_session()
        response = await session.get(
            f"/repos/{owner}/{repo}/pulls",
            params={"state": state, "per_page": self._config.per_page},
        )

        if response.status_code != 200:
            raise GitHubError(
                f"Failed to list pull requests: {response.text}",
                response.status_code,
            )

        prs: list[GitHubPullRequest] = []
        for item in response.json():
            prs.append(GitHubPullRequest(
                id=item["id"],
                number=item["number"],
                title=item["title"],
                body=item.get("body", ""),
                state=item.get("state", "open"),
                author=item["user"]["login"] if item.get("user") else "",
                base_branch=item["base"]["ref"] if item.get("base") else "",
                head_branch=item["head"]["ref"] if item.get("head") else "",
                url=item.get("html_url", ""),
                merged=item.get("merged", False),
                mergeable=item.get("mergeable"),
            ))

        return prs

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify GitHub webhook signature.

        Args:
            payload: Raw request body.
            signature: X-Hub-Signature-256 header value.

        Returns:
            True if signature is valid.
        """
        if not self._config.webhook_secret:
            logger.warning("Webhook secret not configured, skipping verification")
            return True

        import hashlib
        import hmac

        if signature.startswith("sha256="):
            signature = signature[7:]

        expected = hmac.new(
            self._config.webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def parse_webhook_event(
        self,
        event_type: str,
        delivery_id: str,
        payload: dict[str, Any],
        signature: str = "",
    ) -> GitHubWebhookEvent:
        """Parse a GitHub webhook event.

        Args:
            event_type: X-GitHub-Event header value.
            delivery_id: X-GitHub-Delivery header value.
            payload: Request body JSON.
            signature: X-Hub-Signature-256 header value.

        Returns:
            Parsed webhook event.
        """
        return GitHubWebhookEvent(
            event_type=event_type,
            delivery_id=delivery_id,
            payload=payload,
            signature=signature,
        )

    async def create_webhook(
        self,
        owner: str,
        repo: str,
        callback_url: str,
        events: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a repository webhook.

        Args:
            owner: Repository owner.
            repo: Repository name.
            callback_url: Webhook callback URL.
            events: Events to subscribe to.

        Returns:
            Webhook information.

        Raises:
            GitHubError: If creation fails.
        """
        session = await self._get_session()
        payload = {
            "name": "web",
            "active": True,
            "events": events or ["push", "pull_request"],
            "config": {
                "url": callback_url,
                "content_type": "json",
                "secret": self._config.webhook_secret,
            },
        }

        response = await session.post(
            f"/repos/{owner}/{repo}/hooks",
            json=payload,
        )

        if response.status_code != 201:
            raise GitHubError(
                f"Failed to create webhook: {response.text}",
                response.status_code,
            )

        return response.json()


__all__ = [
    "GitHubClient",
    "GitHubConfig",
    "GitHubRepo",
    "GitHubIssue",
    "GitHubPullRequest",
    "GitHubWebhookEvent",
    "GitHubError",
    "GitHubRateLimitError",
    "GitHubAuthError",
]

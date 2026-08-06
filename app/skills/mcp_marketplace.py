"""MCP Plugin Marketplace — browse, install, and configure MCP servers.

Users discover community MCP servers and install them with one click.
Pre-curated popular servers for immediate use.
"""

from __future__ import annotations

import json
import os
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class MCPServerInfo(BaseModel):
    """Metadata for an MCP server in the marketplace."""
    id: str
    name: str
    description: str
    category: str
    author: str = "community"
    icon: str = ""
    install_config: dict[str, Any] = Field(default_factory=dict)
    is_builtin: bool = False
    is_installed: bool = False
    tags: list[str] = Field(default_factory=list)
    popularity: int = 0  # Stars/downloads indicator


# ── Pre-curated MCP Servers ──

MCP_CATALOG: list[MCPServerInfo] = [
    # Development
    MCPServerInfo(
        id="filesystem",
        name="Filesystem",
        description="Read/write files on the local system with sandboxing",
        category="development",
        author="modelcontextprotocol",
        install_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"],
            "env": {},
        },
        is_builtin=True,
        is_installed=True,
        tags=["files", "local", "core"],
        popularity=95,
    ),
    MCPServerInfo(
        id="git",
        name="Git",
        description="Full Git operations: diff, commit, push, pull, log, branch",
        category="development",
        author="modelcontextprotocol",
        install_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-git"],
            "env": {},
        },
        is_builtin=True,
        is_installed=True,
        tags=["git", "version-control"],
        popularity=90,
    ),
    MCPServerInfo(
        id="github",
        name="GitHub",
        description="Issues, PRs, CI runs, code review, repository management",
        category="development",
        author="modelcontextprotocol",
        install_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": ""},
        },
        tags=["github", "pr", "issues", "ci"],
        popularity=88,
    ),
    MCPServerInfo(
        id="gitlab",
        name="GitLab",
        description="GitLab merge requests, issues, CI/CD pipelines",
        category="development",
        author="modelcontextprotocol",
        install_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-gitlab"],
            "env": {"GITLAB_PERSONAL_ACCESS_TOKEN": "", "GITLAB_API_URL": ""},
        },
        tags=["gitlab", "pr", "ci"],
        popularity=70,
    ),
    MCPServerInfo(
        id="docker",
        name="Docker",
        description="Manage containers, images, networks, and volumes",
        category="development",
        author="modelcontextprotocol",
        install_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-docker"],
            "env": {},
        },
        tags=["docker", "containers", "infrastructure"],
        popularity=75,
    ),
    # Database
    MCPServerInfo(
        id="postgres",
        name="PostgreSQL",
        description="Query PostgreSQL with schema inspection and migration support",
        category="database",
        author="modelcontextprotocol",
        install_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-postgres"],
            "env": {"POSTGRESQL_CONNECTION_STRING": ""},
        },
        tags=["database", "sql", "postgres"],
        popularity=85,
    ),
    MCPServerInfo(
        id="sqlite",
        name="SQLite",
        description="Lightweight local database queries",
        category="database",
        author="modelcontextprotocol",
        install_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-sqlite", "/workspace/data.db"],
            "env": {},
        },
        tags=["database", "sql", "sqlite"],
        popularity=80,
    ),
    MCPServerInfo(
        id="redis",
        name="Redis",
        description="Key-value store operations, caching, pub/sub",
        category="database",
        author="modelcontextprotocol",
        install_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-redis"],
            "env": {"REDIS_URL": "redis://localhost:6379"},
        },
        tags=["database", "cache", "redis"],
        popularity=72,
    ),
    MCPServerInfo(
        id="mongodb",
        name="MongoDB",
        description="Document database queries and aggregation",
        category="database",
        author="community",
        install_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-mongodb"],
            "env": {"MONGODB_CONNECTION_STRING": ""},
        },
        tags=["database", "nosql", "mongodb"],
        popularity=65,
    ),
    # Research
    MCPServerInfo(
        id="brave-search",
        name="Brave Search",
        description="Web search with Brave Search API (1000 queries/month free)",
        category="research",
        author="modelcontextprotocol",
        install_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "env": {"BRAVE_API_KEY": ""},
        },
        tags=["search", "web", "research"],
        popularity=82,
    ),
    MCPServerInfo(
        id="fetch",
        name="Fetch",
        description="HTTP requests with smart content extraction",
        category="research",
        author="modelcontextprotocol",
        install_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-fetch"],
            "env": {},
        },
        tags=["http", "fetch", "web"],
        popularity=78,
    ),
    MCPServerInfo(
        id="puppeteer",
        name="Puppeteer",
        description="Browser automation — navigate, click, screenshot, scrape JS-heavy pages",
        category="research",
        author="modelcontextprotocol",
        install_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
            "env": {},
        },
        tags=["browser", "scraping", "automation"],
        popularity=80,
    ),
    MCPServerInfo(
        id="sequential-thinking",
        name="Sequential Thinking",
        description="Step-by-step reasoning for complex problems",
        category="research",
        author="modelcontextprotocol",
        install_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
            "env": {},
        },
        tags=["reasoning", "thinking", "analysis"],
        popularity=75,
    ),
    # Communication
    MCPServerInfo(
        id="slack",
        name="Slack",
        description="Read and send Slack messages, manage channels",
        category="communication",
        author="modelcontextprotocol",
        install_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-slack"],
            "env": {"SLACK_BOT_TOKEN": "", "SLACK_TEAM_ID": ""},
        },
        tags=["slack", "messaging", "team"],
        popularity=70,
    ),
    MCPServerInfo(
        id="discord",
        name="Discord",
        description="Send messages and manage Discord channels",
        category="communication",
        author="community",
        install_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-discord"],
            "env": {"DISCORD_BOT_TOKEN": ""},
        },
        tags=["discord", "messaging", "community"],
        popularity=60,
    ),
    # Productivity
    MCPServerInfo(
        id="notion",
        name="Notion",
        description="Read and write Notion pages and databases",
        category="productivity",
        author="modelcontextprotocol",
        install_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-notion"],
            "env": {"NOTION_TOKEN": ""},
        },
        tags=["notion", "docs", "database"],
        popularity=72,
    ),
    MCPServerInfo(
        id="google-maps",
        name="Google Maps",
        description="Location search, directions, places, geocoding",
        category="productivity",
        author="modelcontextprotocol",
        install_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-google-maps"],
            "env": {"GOOGLE_MAPS_API_KEY": ""},
        },
        tags=["maps", "location", "travel"],
        popularity=65,
    ),
    MCPServerInfo(
        id="memory",
        name="Memory",
        description="Persistent key-value memory for agents (cross-session)",
        category="productivity",
        author="modelcontextprotocol",
        install_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"],
            "env": {},
        },
        tags=["memory", "storage", "persistence"],
        popularity=70,
    ),
    # Cloud
    MCPServerInfo(
        id="aws",
        name="AWS",
        description="AWS service management: S3, Lambda, EC2, DynamoDB",
        category="cloud",
        author="community",
        install_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-aws"],
            "env": {"AWS_ACCESS_KEY_ID": "", "AWS_SECRET_ACCESS_KEY": "", "AWS_REGION": "us-east-1"},
        },
        tags=["aws", "cloud", "infrastructure"],
        popularity=68,
    ),
    MCPServerInfo(
        id="cloudflare",
        name="Cloudflare",
        description="Workers, KV, R2, D1 — full Cloudflare edge computing",
        category="cloud",
        author="modelcontextprotocol",
        install_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-cloudflare"],
            "env": {"CLOUDFLARE_API_TOKEN": "", "CLOUDFLARE_ACCOUNT_ID": ""},
        },
        tags=["cloudflare", "workers", "edge"],
        popularity=62,
    ),
    # ── User-Requested MCPs ──
    MCPServerInfo(
        id="playwright",
        name="Playwright",
        description="Browser automation: navigate, click, screenshot, fill forms",
        category="automation",
        author="microsoft",
        install_config={
            "command": "npx",
            "args": ["-y", "@playwright/mcp@latest"],
            "env": {},
        },
        tags=["browser", "automation", "testing", "scraping"],
        popularity=92,
    ),
    MCPServerInfo(
        id="sequential-thinking",
        name="Sequential Thinking",
        description="Structured multi-step reasoning with revision and branching",
        category="reasoning",
        author="modelcontextprotocol",
        install_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
            "env": {},
        },
        tags=["reasoning", "thinking", "planning"],
        popularity=88,
    ),
    MCPServerInfo(
        id="memory-bank",
        name="Memory Bank",
        description="Persistent cross-session memory with semantic recall",
        category="memory",
        author="modelcontextprotocol",
        install_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"],
            "env": {},
        },
        tags=["memory", "persistence", "recall"],
        popularity=85,
    ),
    MCPServerInfo(
        id="context7",
        name="Context7",
        description="Up-to-date documentation and code context for any library",
        category="research",
        author="context7",
        install_config={
            "command": "npx",
            "args": ["-y", "@upstash/context7-mcp"],
            "env": {},
        },
        tags=["docs", "documentation", "context", "libraries"],
        popularity=90,
    ),
    MCPServerInfo(
        id="markitdown",
        name="MarkItDown",
        description="Convert PDF, DOCX, PPTX, HTML, images to Markdown",
        category="conversion",
        author="microsoft",
        install_config={
            "command": "npx",
            "args": ["-y", "@microsoft/markitdown-mcp@latest"],
            "env": {},
        },
        tags=["markdown", "conversion", "documents", "pdf"],
        popularity=82,
    ),
    MCPServerInfo(
        id="brave-search",
        name="Brave Search",
        description="Web search via Brave Search API with region and localization",
        category="research",
        author="modelcontextprotocol",
        install_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "env": {"BRAVE_API_KEY": ""},
        },
        tags=["search", "web", "research"],
        popularity=87,
    ),
    MCPServerInfo(
        id="fetch",
        name="Fetch",
        description="HTTP requests with content extraction and summarization",
        category="research",
        author="modelcontextprotocol",
        install_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-fetch"],
            "env": {},
        },
        tags=["http", "fetch", "web", "scraping"],
        popularity=80,
    ),
    MCPServerInfo(
        id="puppeteer",
        name="Puppeteer",
        description="Headless Chrome automation for web scraping and testing",
        category="automation",
        author="anthropic",
        install_config={
            "command": "npx",
            "args": ["-y", "@anthropic-ai/mcp-puppeteer"],
            "env": {},
        },
        tags=["browser", "chrome", "scraping", "automation"],
        popularity=78,
    ),
    MCPServerInfo(
        id="postgres",
        name="PostgreSQL",
        description="Query PostgreSQL with schema inspection and SQL execution",
        category="database",
        author="modelcontextprotocol",
        install_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-postgres"],
            "env": {"POSTGRES_CONNECTION_STRING": ""},
        },
        tags=["database", "sql", "postgres"],
        popularity=83,
    ),
]


class MCPMarketplace:
    """Manages MCP server discovery, installation, and configuration."""

    def __init__(self, config_path: str = "/workspace/.mcp_servers.json"):
        self.config_path = config_path
        self._servers: dict[str, MCPServerInfo] = {}
        self._load_builtins()
        self._load_installed()

    def _load_builtins(self):
        for server in MCP_CATALOG:
            self._servers[server.id] = server

    def _load_installed(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path) as f:
                    data = json.load(f)
                for sid, cfg in data.items():
                    if sid not in self._servers:
                        self._servers[sid] = MCPServerInfo(
                            id=sid,
                            name=cfg.get("name", sid),
                            description=cfg.get("description", ""),
                            category=cfg.get("category", "custom"),
                            install_config=cfg.get("install_config", {}),
                            is_installed=True,
                        )
                    else:
                        self._servers[sid].is_installed = True
                        if cfg.get("env"):
                            self._servers[sid].install_config["env"] = cfg["env"]
            except (OSError, json.JSONDecodeError):
                pass

    def _save_installed(self):
        data = {}
        for sid, server in self._servers.items():
            if server.is_installed and not server.is_builtin:
                data[sid] = {
                    "name": server.name,
                    "description": server.description,
                    "category": server.category,
                    "install_config": server.install_config,
                    "env": server.install_config.get("env", {}),
                }
        try:
            with open(self.config_path, "w") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            logger.error("Failed to save MCP config", error=str(e))

    def list_servers(
        self,
        category: str | None = None,
        installed_only: bool = False,
        search: str | None = None,
    ) -> list[MCPServerInfo]:
        results = list(self._servers.values())
        if installed_only:
            results = [s for s in results if s.is_installed]
        if category:
            results = [s for s in results if s.category == category]
        if search:
            search_lower = search.lower()
            results = [
                s for s in results
                if search_lower in s.name.lower()
                or search_lower in s.description.lower()
                or any(search_lower in t for t in s.tags)
            ]
        # Sort by popularity
        results.sort(key=lambda s: -s.popularity)
        return results

    def get_server(self, server_id: str) -> MCPServerInfo | None:
        return self._servers.get(server_id)

    def install_server(self, server_id: str, env_overrides: dict[str, str] | None = None) -> bool:
        server = self._servers.get(server_id)
        if not server:
            return False
        if env_overrides:
            server.install_config.setdefault("env", {}).update(env_overrides)
        server.is_installed = True
        self._save_installed()
        logger.info("MCP server installed", id=server_id, name=server.name)
        return True

    def uninstall_server(self, server_id: str) -> bool:
        server = self._servers.get(server_id)
        if not server or server.is_builtin:
            return False
        server.is_installed = False
        self._save_installed()
        return True

    def configure_server(self, server_id: str, env: dict[str, str]) -> bool:
        server = self._servers.get(server_id)
        if not server:
            return False
        server.install_config.setdefault("env", {}).update(env)
        if server.is_installed:
            self._save_installed()
        return True

    def get_categories(self) -> list[str]:
        return sorted(set(s.category for s in self._servers.values()))

    def get_install_config(self, server_id: str) -> dict[str, Any] | None:
        server = self._servers.get(server_id)
        if not server or not server.is_installed:
            return None
        return server.install_config


# Backward compatibility
BUILTIN_MCP_SERVERS = MCP_CATALOG

# Global singleton
mcp_marketplace = MCPMarketplace()
